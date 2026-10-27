
import time

from fastapi import HTTPException, Request


REQUEST_LIMIT = 5
WINDOW_SECONDS = 60

request_counts = {}


def check_rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()

    if client_ip not in request_counts:
        request_counts[client_ip] = {
            "count": 0,
            "start_time": current_time
        }

    client_data = request_counts[client_ip]

    elapsed_time = current_time - client_data["start_time"]

    # Reset the window after 60 seconds
    if elapsed_time >= WINDOW_SECONDS:
        client_data["count"] = 0
        client_data["start_time"] = current_time

    # Reject the request if the limit has been reached
    if client_data["count"] >= REQUEST_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    # Count this request
    client_data["count"] += 1
