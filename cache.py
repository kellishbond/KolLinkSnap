
import logging
import os

import redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)

# Cached URLs expire after five minutes.
CACHE_TTL_SECONDS = 300

# Allow the Redis address to be configured during deployment.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def get_cached_url(short_code: str) -> str | None:
    """Return a cached URL, or None if missing or Redis is unavailable."""
    key = f"kollinksnap:url:{short_code}"

    try:
        return redis_client.get(key)
    except RedisError:
        logger.warning(
            "Redis unavailable while reading cache; falling back to SQLite."
        )
        return None


def cache_url(short_code: str, original_url: str) -> None:
    """Cache a URL for five minutes when Redis is available."""
    key = f"kollinksnap:url:{short_code}"

    try:
        redis_client.set(
            key,
            original_url,
            ex=CACHE_TTL_SECONDS,
        )
    except RedisError:
        logger.warning(
            "Redis unavailable while writing cache; continuing without caching."
        )
