
import ipaddress
import secrets
import string

from fastapi import APIRouter, FastAPI, HTTPException, Path, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, field_validator

from cache import cache_url, get_cached_url
from database import create_table, get_connection
from limiter import check_rate_limit


app = FastAPI(title="KolLinkSnap")

# Make sure the database table exists
create_table()

# Group version 1 API endpoints
api_router = APIRouter(prefix="/api/v1")


class LinkCreate(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def reject_unsafe_destinations(cls, url: HttpUrl) -> HttpUrl:
        hostname = url.host.lower().rstrip(".")

        # Do not allow local hostnames.
        if (
            hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname.endswith(".local")
        ):
            raise ValueError("Local destinations are not allowed")

        # Reject literal IP addresses that are not publicly routable.
        try:
            ip_address = ipaddress.ip_address(hostname)
        except ValueError:
            ip_address = None

        if ip_address is not None and (
            not ip_address.is_global
        ):
            raise ValueError("Non-public IP addresses are not allowed")

        # Do not allow URLs containing embedded login credentials.
        if url.username is not None or url.password is not None:
            raise ValueError("URLs containing credentials are not allowed")

        return url


@api_router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "KolLinkSnap"
    }


@api_router.post("/shorten")
def shorten_url(link: LinkCreate, request: Request):
    check_rate_limit(request)

    characters = string.ascii_letters + string.digits
    connection = get_connection()

    try:
        # Generate a unique short code.
        while True:
            short_code = "".join(
                secrets.choice(characters) for _ in range(6)
            )

            existing_link = connection.execute(
                "SELECT short_code FROM links WHERE short_code = ?",
                (short_code,)
            ).fetchone()

            if existing_link is None:
                break

        original_url = str(link.url)

        connection.execute(
            """
            INSERT INTO links (short_code, original_url, clicks)
            VALUES (?, ?, 0)
            """,
            (short_code, original_url)
        )

        connection.commit()

        return {
            "short_code": short_code,
            "original_url": original_url,
            "clicks": 0
        }

    finally:
        connection.close()


@api_router.get("/stats/{short_code}")
def get_link_stats(
    short_code: str = Path(
        min_length=6,
        max_length=6,
        pattern=r"^[A-Za-z0-9]{6}$"
    )
):
    connection = get_connection()

    try:
        link_data = connection.execute(
            "SELECT * FROM links WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        if link_data is None:
            raise HTTPException(
                status_code=404,
                detail="Short link not found"
            )

        return {
            "short_code": link_data["short_code"],
            "original_url": link_data["original_url"],
            "clicks": link_data["clicks"]
        }

    finally:
        connection.close()


app.include_router(api_router)


@app.get("/{short_code}")
def redirect_url(
    short_code: str = Path(
        min_length=6,
        max_length=6,
        pattern=r"^[A-Za-z0-9]{6}$"
    )
):
    original_url = get_cached_url(short_code)

    connection = get_connection()

    try:
        # If the URL is not cached, look it up in SQLite.
        if original_url is None:
            link_data = connection.execute(
                """
                SELECT original_url
                FROM links
                WHERE short_code = ?
                """,
                (short_code,)
            ).fetchone()

            if link_data is None:
                raise HTTPException(
                    status_code=404,
                    detail="Short link not found"
                )

            original_url = link_data["original_url"]
            cache_url(short_code, original_url)

        # Record every successful visit.
        connection.execute(
            """
            UPDATE links
            SET clicks = clicks + 1
            WHERE short_code = ?
            """,
            (short_code,)
        )

        connection.commit()

        return RedirectResponse(url=original_url)

    finally:
        connection.close()
