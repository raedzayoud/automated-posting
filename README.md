# Automated Multi-Platform Posting System

FastAPI service that publishes one short message (with exactly one CTA link) to five
third-party platforms through their official APIs, and reports the outcome of every
platform independently.

`POST http://localhost:4000/posting`

## Platforms

| Platform | API | Auth | Public post URL |
|---|---|---|---|
| Bluesky | `com.atproto.server.createSession` + `com.atproto.repo.createRecord` | handle + app password | `https://bsky.app/profile/<handle>/post/<rkey>` |
| Mastodon | `POST /api/v1/statuses` | instance access token | `url` returned by the API |
| Dev.to | `POST /api/articles` (Forem API v1) | `api-key` header | `url` returned by the API |
| WordPress | `POST /wp-json/wp/v2/posts` | Basic auth (Application Password) | `link` returned by the API |
| Hugging Face | `POST /api/models/{repo}/discussions` | user access token (write) | `https://huggingface.co/<repo>/discussions/<num>` |

Platforms that were researched and rejected, and why:

- **X (Twitter)** - pay-per-use since Feb 2026; a post containing a URL costs **$0.20**. Unreasonable for a demo.
- **Reddit** - new public Data API requests closed on 31 Oct 2026; cannot obtain credentials.
- **LinkedIn / Facebook / Instagram** - require app review and business verification (days of lead time).

## Project structure

```
app/
  main.py                 FastAPI app: POST /posting, GET /health
  schemas.py              request/response models + message validation
  config.py               pydantic-settings, reads .env
  platforms/
    base.py               PlatformAdapter ABC, shared helpers
    bluesky.py            one adapter per platform
    mastodon.py
    devto.py
    wordpress.py
    huggingface.py
  services/
    posting_service.py    concurrent fan-out, per-platform isolation
tests/
  test_posting.py         11 tests, no network (httpx.MockTransport)
```

## Setup

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On Linux/macOS use `python3 -m venv venv` and `venv/bin/python -m pip install -r requirements.txt`.

> Use `python -m pip`, not `pip.exe`: on machines with an application-control
> policy the `pip` shim can be blocked even though the module works.

### Credentials

Fill `.env` (never commit it - it is in `.gitignore`):

| Variable | Where to get it |
|---|---|
| `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | bsky.app -> Settings -> App Passwords |
| `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | instance -> Preferences -> Development -> New application, scope `write:statuses` |
| `DEVTO_API_KEY` | dev.to -> Settings -> Extensions -> DEV Community API Keys |
| `WORDPRESS_SITE_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` | WP Admin -> Users -> Profile -> Application Passwords (site must be HTTPS) |
| `HF_TOKEN`, `HF_REPO` | huggingface.co -> Settings -> Access Tokens (role **Write**); `HF_REPO` is an existing **public** model repo, e.g. `yourname/automated-posting-demo` |

All variables are optional. A platform missing credentials is reported as `failed`
with `missing credentials: <ENV_VAR>`; it never blocks the other platforms.

## Run

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 4000
```

OpenAPI docs: <http://localhost:4000/docs>

## Usage

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

### Request

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

### Validation rules

- The message is trimmed and must be **1-200 characters**.
- It must contain **exactly one** CTA link (`http://` or `https://`).
- The link must have a scheme of `http`/`https` and a host containing a dot.
- Trailing punctuation after a link (`https://example.com.`) is not treated as part of the URL.

Invalid input returns **422** with a single human-readable reason:

```json
{"detail": "Message must contain exactly one CTA link, found 2."}
```

### Response

`200` once the message is accepted - per-platform failures are reported inside the body.
`success` is `true` when at least one platform published. `date`/`time` are UTC.

```json
{
  "success": true,
  "results": [
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/tester.bsky.social/post/3labc123",
      "public_access": true,
      "date": "2026-11-17",
      "time": "09:41:07",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.online/@tester/1134567890",
      "public_access": true,
      "date": "2026-11-17",
      "time": "09:41:08",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/tester/check-out-our-latest-business-platform-4f2",
      "public_access": true,
      "date": "2026-11-17",
      "time": "09:41:10",
      "error": null
    },
    {
      "platform": "WordPress",
      "status": "success",
      "posted_url": "https://blog.example.com/2026/11/17/check-out-our-latest-business-platform/",
      "public_access": true,
      "date": "2026-11-17",
      "time": "09:41:11",
      "error": null
    },
    {
      "platform": "Hugging Face",
      "status": "success",
      "posted_url": "https://huggingface.co/tester/automated-posting-demo/discussions/1",
      "public_access": true,
      "date": "2026-11-17",
      "time": "09:41:12",
      "error": null
    }
  ]
}
```

Failure isolation example (Dev.to rejected the write, everything else succeeded):

```json
{
  "success": true,
  "results": [
    {"platform": "Dev.to", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "HTTP 401: {\"error\":\"unauthorized\",\"status\":401}"},
    {"platform": "Mastodon", "status": "success", "posted_url": "https://mastodon.online/@tester/1134567890", "public_access": true, "date": "2026-11-17", "time": "09:41:08", "error": null}
  ]
}
```

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

11 tests, no network access - `httpx.MockTransport` fakes every platform API. They cover:
validation (length, missing/duplicate/malformed link, trailing punctuation, 200-char boundary),
a full 5-platform fan-out, one platform returning HTTP 500 while the others succeed,
and the all-missing-credentials case.

## Live verification

Run the server, send the request, and keep the evidence in `docs/screenshots/`:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 4000
curl.exe -X POST http://localhost:4000/posting -H "Content-Type: application/json" -d '{\"message\": \"Check out our latest business platform and grow your online visibility. https://example.com\"}'
```

Screenshots of the response, the server log, the generated `/docs` page, and the five
public posts are stored in [`docs/screenshots/`](docs/screenshots/).

## Design notes

- Adapters are independent: one shared `httpx.AsyncClient`, concurrent `asyncio.gather`
  with `return_exceptions=True`, and a 15 s timeout per request.
- Errors are flattened to one line and truncated to 300 characters. No request headers,
  tokens or passwords are ever echoed back.
- `public_access` is derived from the platform response: Mastodon `visibility == "public"`,
  WordPress `status == "publish"`, Bluesky and Hugging Face posts are public by nature.
- Article-style platforms need a title; it is derived from the text before the link
  (60 chars, fallback `New update`).

## Out of scope

Scheduling, persistence, retries/backoff, authentication on the endpoint itself,
and deletion of published posts.

## Security

- Credentials live only in `.env`, which is git-ignored (`.env.example` holds empty names).
- Tokens are sent only in headers/JSON to their own platform, never logged.
- WordPress uses Application Passwords (revocable individually) over HTTPS.
