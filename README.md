
# KolLinkSnap

KolLinkSnap is a simple URL shortener API built with Python, FastAPI, and SQLite.

It converts long URLs into short codes, redirects visitors to the original URLs, and tracks the number of clicks.

## Features

- Create short links.
- Redirect visitors using a short code.
- Track clicks for each short link.
- Retrieve link statistics.
- Validate submitted URLs.
- Rate-limit link creation requests.
- Cache destination URLs in memory with a five-minute expiry.
- Store links and click counts in SQLite.
- Use versioned API endpoints.
- Run automated tests with pytest.

## Technology Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- SQLite
- pytest

## Project Structure

```text
KolLinkSnap/
├── main.py
├── database.py
├── cache.py
├── limiter.py
├── requirements.txt
├── README.md
├── .gitignore
└── tests/
    └── test_main.py
```

## Requirements

- Python 3.12 or newer
- pip
- Git (optional)

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd KolLinkSnap
```

Replace `<YOUR_REPOSITORY_URL>` with your actual Git repository URL.

If you already have the project locally, navigate to its folder instead.

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

On Linux or macOS:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Run the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs

Health endpoint:

http://127.0.0.1:8000/api/v1/health

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Check application health |
| POST | `/api/v1/shorten` | Create a short link |
| GET | `/api/v1/stats/{short_code}` | Retrieve link statistics |
| GET | `/{short_code}` | Redirect to the original URL |

### 1. Check application health

Request:

```http
GET /api/v1/health
```

Example response:

```json
{
  "status": "healthy",
  "app": "KolLinkSnap"
}
```

### 2. Create a short link

Request:

```http
POST /api/v1/shorten
Content-Type: application/json
```

Example body:

```json
{
  "url": "https://example.com"
}
```

Example response:

```json
{
  "short_code": "aB12xY",
  "original_url": "https://example.com/",
  "clicks": 0
}
```

The generated short code in this example is illustrative.

### 3. Redirect to the original URL

Open the following URL in your browser, replacing the example code with a code returned by the API:

```text
http://127.0.0.1:8000/aB12xY
```

The API responds with a redirect to the original destination.

### 4. Retrieve link statistics

Request:

```http
GET /api/v1/stats/aB12xY
```

Example response:

```json
{
  "short_code": "aB12xY",
  "original_url": "https://example.com/",
  "clicks": 3
}
```

The click count depends on the actual visits to that link.

## Testing

Run the automated test suite:

```bash
python -m pytest -q
```

The tests cover the health endpoint, link creation, missing links, redirects, click tracking, URL validation, rate limiting, and caching.

## Database

KolLinkSnap uses SQLite to store shortened links.

The `links` table contains:

- `short_code`: unique short code and primary key.
- `original_url`: original destination URL.
- `clicks`: number of successful redirects recorded.

The database table is initialized by the application. The local database file is excluded from Git, so a new installation can create its own database.

## Caching

Destination URLs are cached in application memory for five minutes.

When an entry expires, the application can retrieve the destination from SQLite and cache it again.

The cache is local to each running process and is cleared when that process restarts.

## Rate Limiting

The current implementation limits link creation to five requests per 60-second window per tracked client IP address.

The rate limiter stores its state in memory. It resets when the application restarts and does not share state across multiple worker processes.

## Security Notes

The application validates submitted URLs and rejects certain local destinations and non-public literal IP addresses.

This is a learning project and its safeguards are not a complete malicious-link detection system. Additional security review is needed before exposing the service publicly.

For production use, consider:

- Stronger destination and redirect-abuse protections.
- Shared rate limiting with Redis.
- Persistent or shared caching where appropriate.
- A persistent database suitable for the deployment environment.
- HTTPS and appropriate proxy configuration.
- Monitoring, logging, and abuse reporting.

## Current Limitations

- Short codes are six alphanumeric characters.
- Cache and rate-limit state are stored in memory.
- SQLite is suitable for learning and small demos but may not suit every production workload.
- The project currently provides an API rather than a complete web interface.
- The development server should not be treated as a complete production deployment setup.

## Learning Objectives

This project demonstrates:

- REST API design and versioning.
- URL validation with Pydantic.
- SQL queries and persistent storage.
- Database indexing and query-plan inspection.
- Caching and cache expiration.
- Rate limiting.
- Automated API testing.
- Basic security considerations.

## License

No license has been specified yet. Add a license before distributing the project for reuse.
