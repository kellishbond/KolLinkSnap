import secrets
import string

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from database import create_table, get_connection

app = FastAPI()

# Make sure the database table exists
create_table()


class LinkCreate(BaseModel):
    url: HttpUrl


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "KolLinkSnap"
    }


@app.post("/shorten")
def shorten_url(link: LinkCreate):
    characters = string.ascii_letters + string.digits

    connection = get_connection()

    try:
        # Generate a unique short code
        while True:
            short_code = ''.join(
                secrets.choice(characters) for _ in range(6)
            )

            existing_link = connection.execute(
                "SELECT short_code FROM links WHERE short_code = ?",
                (short_code,)
            ).fetchone()

            if existing_link is None:
                break

        original_url = str(link.url)

        # Save the new link in SQLite
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


@app.get("/stats/{short_code}")
def get_link_stats(short_code: str):
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


@app.get("/{short_code}")
def redirect_url(short_code: str):
    connection = get_connection()

    try:
        link_data = connection.execute(
            "SELECT original_url FROM links WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        if link_data is None:
            raise HTTPException(
                status_code=404,
                detail="Short link not found"
            )

        # Increase the click count in the database
        connection.execute(
            """
            UPDATE links
            SET clicks = clicks + 1
            WHERE short_code = ?
            """,
            (short_code,)
        )

        connection.commit()

        return RedirectResponse(
            url=link_data["original_url"]
        )

    finally:
        connection.close()