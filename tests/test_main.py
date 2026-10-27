
import pytest
from fastapi.testclient import TestClient
import limiter
import cache
import main
from redis.exceptions import RedisError

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_kollinksnap.db"

    # Use a separate temporary SQLite database for each test.
    monkeypatch.setattr(
        main,
        "get_connection",
        lambda: get_connection_for_test(test_database)
    )

    monkeypatch.setattr(
        main,
        "create_table",
        lambda: create_table_for_test(test_database)
    )

    # Reset rate-limit counters before each test.
    # monkeypatch.setattr(limiter, "request_counts", {})
    clear_rate_limit_counters()

    # Clear only KolLinkSnap's Redis cache keys.
    clear_url_cache()

    create_table_for_test(test_database)

    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        clear_url_cache()


def clear_url_cache():
    """Delete KolLinkSnap cache entries without clearing all Redis data."""
    for key in cache.redis_client.scan_iter(
        match="kollinksnap:url:*"
    ):
        cache.redis_client.delete(key)


def clear_rate_limit_counters():
    """Delete KolLinkSnap rate-limit keys."""
    for key in cache.redis_client.scan_iter(
        match="kollinksnap:ratelimit:*"
    ):
        cache.redis_client.delete(key)

def get_connection_for_test(database_path):
    import sqlite3

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_table_for_test(database_path):
    connection = get_connection_for_test(database_path)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0
            )
        """)
        connection.commit()
    finally:
        connection.close()


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_shorten_url(client):
    response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["short_code"]) == 6
    assert data["original_url"] == "https://example.com/"
    assert data["clicks"] == 0


def test_missing_short_link_returns_404(client):
    response = client.get("/api/v1/stats/ZZ99XX")

    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


def test_click_count_increases(client):
    create_response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    short_code = create_response.json()["short_code"]

    first_visit = client.get(
        f"/{short_code}",
        follow_redirects=False
    )

    assert first_visit.status_code == 307

    stats_response = client.get(
        f"/api/v1/stats/{short_code}"
    )

    assert stats_response.status_code == 200
    assert stats_response.json()["clicks"] == 1


def test_missing_redirect_link_returns_404(client):
    response = client.get(
        "/ZZ99XX",
        follow_redirects=False
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


def test_invalid_url_is_rejected(client):
    response = client.post(
        "/api/v1/shorten",
        json={"url": "not-a-valid-url"}
    )

    assert response.status_code == 422


def test_sixth_shorten_request_is_rate_limited(client):
    for _ in range(5):
        response = client.post(
            "/api/v1/shorten",
            json={"url": "https://example.com"}
        )

        assert response.status_code == 200

    response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Rate limit exceeded. Try again later."
    )


def test_redirect_caches_original_url(client):
    create_response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    short_code = create_response.json()["short_code"]

    assert cache.get_cached_url(short_code) is None

    response = client.get(
        f"/{short_code}",
        follow_redirects=False
    )

    assert response.status_code == 307
    assert cache.get_cached_url(short_code) == "https://example.com/"


def test_cached_redirect_still_increases_clicks(client):
    create_response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    short_code = create_response.json()["short_code"]

    first_visit = client.get(
        f"/{short_code}",
        follow_redirects=False
    )

    assert first_visit.status_code == 307
    assert cache.get_cached_url(short_code) is not None

    second_visit = client.get(
        f"/{short_code}",
        follow_redirects=False
    )

    assert second_visit.status_code == 307

    stats_response = client.get(
        f"/api/v1/stats/{short_code}"
    )

    assert stats_response.status_code == 200
    assert stats_response.json()["clicks"] == 2


def test_cached_url_expires_after_five_minutes(client):
    cache.cache_url("expire1", "https://example.com/")

    ttl = cache.redis_client.ttl("kollinksnap:url:expire1")

    assert 0 < ttl <= cache.CACHE_TTL_SECONDS


def test_redirect_falls_back_to_sqlite_when_redis_fails(
    client, monkeypatch
):
    create_response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    assert create_response.status_code == 200
    short_code = create_response.json()["short_code"]

    def redis_unavailable(*args, **kwargs):
        raise RedisError("Redis unavailable")

    # Simulate Redis failing during cache reads and writes.
    monkeypatch.setattr(
        cache.redis_client, "get", redis_unavailable
    )
    monkeypatch.setattr(
        cache.redis_client, "set", redis_unavailable
    )

    response = client.get(
        f"/{short_code}",
        follow_redirects=False
    )

    # The app should still redirect using the SQLite record.
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"


def test_rate_limiter_returns_503_when_redis_fails(
    client, monkeypatch
):
    def redis_unavailable(*args, **kwargs):
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        limiter.redis_client, "eval", redis_unavailable
    )

    response = client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Rate limiting service unavailable. Try again later."
    )