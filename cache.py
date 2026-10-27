
import time

# Cached entries expire after 5 minutes.
CACHE_TTL_SECONDS = 300

# Store each URL together with the time it expires.
url_cache = {}


def get_cached_url(short_code: str):
    """Return a cached URL if it has not expired."""
    cached_entry = url_cache.get(short_code)

    if cached_entry is None:
        return None

    original_url, expires_at = cached_entry

    # Remove expired entries instead of returning stale data.
    if time.time() >= expires_at:
        del url_cache[short_code]
        return None

    return original_url


def cache_url(short_code: str, original_url: str):
    """Cache a URL for five minutes."""
    expires_at = time.time() + CACHE_TTL_SECONDS

    url_cache[short_code] = (original_url, expires_at)
