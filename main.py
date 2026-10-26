import secrets
import string

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI()

# Store short codes, original URLs, and click counts
links = {}


class LinkCreate(BaseModel):
    url: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "KolLinkSnap"
    }


@app.post("/shorten")
def shorten_url(link: LinkCreate):
    characters = string.ascii_letters + string.digits

    short_code = ''.join(
        secrets.choice(characters) for _ in range(6)
    )

    # Save the URL and initialize its click count
    links[short_code] = {
        "original_url": link.url,
        "clicks": 0
    }

    return {
        "short_code": short_code,
        "original_url": link.url,
        "clicks": 0
    }


@app.get("/stats/{short_code}")
def get_link_stats(short_code: str):
    link_data = links.get(short_code)

    if link_data is None:
        raise HTTPException(
            status_code=404,
            detail="Short link not found"
        )

    return {
        "short_code": short_code,
        "original_url": link_data["original_url"],
        "clicks": link_data["clicks"]
    }


@app.get("/{short_code}")
def redirect_url(short_code: str):
    link_data = links.get(short_code)

    if link_data is None:
        raise HTTPException(
            status_code=404,
            detail="Short link not found"
        )

    # Increase the click count by one
    link_data["clicks"] += 1

    # Redirect the visitor to the original URL
    return RedirectResponse(
        url=link_data["original_url"]
    )
