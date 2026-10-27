
from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from cache import redis_client


REQUEST_LIMIT = 5
WINDOW_SECONDS = 60

INCREMENT_COUNTER_SCRIPT = """
local count = redis.call("INCR", KEYS[1])

if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

return count
"""


def check_rate_limit(request: Request):
    """Allow at most five requests per IP in a 60-second window."""
    client_ip = request.client.host if request.client else "unknown"

    key = f"kollinksnap:ratelimit:shorten:{client_ip}"

    try:
        request_count = redis_client.eval(
            INCREMENT_COUNTER_SCRIPT,
            1,
            key,
            WINDOW_SECONDS,
        )
    except RedisError:
        # Fail safely rather than bypassing rate limiting.
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable. Try again later.",
        )

    if request_count > REQUEST_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )
