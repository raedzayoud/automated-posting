import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.platforms.base import PlatformAdapter
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.huggingface import HuggingFaceAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.wordpress import WordPressAdapter
from app.schemas import validate_message
from app.services.posting_service import PostingService

MESSAGE = "Check out our latest business platform and grow your online visibility. https://example.com"

CREDENTIALS = {
    "bluesky_handle": "tester.bsky.social",
    "bluesky_app_password": "app-password",
    "mastodon_base_url": "https://mastodon.online",
    "mastodon_access_token": "mastodon-token",
    "devto_api_key": "devto-key",
    "wordpress_site_url": "https://blog.example.com",
    "wordpress_username": "writer",
    "wordpress_app_password": "wp-app-password",
    "hf_token": "hf_token",
    "hf_repo": "tester/demo",
}


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    for field, value in CREDENTIALS.items():
        monkeypatch.setattr(settings, field, value)


def handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "com.atproto.server.createSession" in url:
        return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:abc", "handle": "tester.bsky.social"})
    if "com.atproto.repo.createRecord" in url:
        return httpx.Response(200, json={"uri": "at://did:plc:abc/app.bsky.feed.post/xyz123", "cid": "cid"})
    if url.endswith("/api/v1/statuses"):
        return httpx.Response(200, json={"url": "https://mastodon.online/@tester/1", "visibility": "public"})
    if url.endswith("/api/articles"):
        return httpx.Response(201, json={"url": "https://dev.to/tester/post-1"})
    if url.endswith("/wp-json/wp/v2/posts"):
        return httpx.Response(201, json={"link": "https://blog.example.com/hello", "status": "publish"})
    if url.endswith("/discussions"):
        return httpx.Response(200, json={"url": "https://huggingface.co/tester/demo/discussions/1", "num": 1})
    return httpx.Response(404, json={"error": "unexpected url"})


def publish(transport_handler=handler, message=MESSAGE):
    adapters = [BlueskyAdapter(), MastodonAdapter(), DevToAdapter(), WordPressAdapter(), HuggingFaceAdapter()]
    service = PostingService(adapters, transport=httpx.MockTransport(transport_handler))
    return asyncio.run(service.publish(message))


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_base_adapter_is_abstract():
    with pytest.raises(TypeError):
        PlatformAdapter()


def test_rejects_message_over_200_characters():
    response = TestClient(app).post("/posting", json={"message": "a" * 201})
    assert response.status_code == 422
    assert "200 characters" in response.text


def test_rejects_message_without_link():
    response = TestClient(app).post("/posting", json={"message": "No link here"})
    assert response.status_code == 422
    assert "exactly one CTA link" in response.text


def test_rejects_two_links():
    response = TestClient(app).post("/posting", json={"message": "One https://a.com and two https://b.com"})
    assert response.status_code == 422
    assert "found 2" in response.text


def test_rejects_malformed_url():
    with pytest.raises(ValueError, match="valid http"):
        validate_message("Visit https://exa mple")


def test_accepts_link_followed_by_punctuation():
    assert validate_message("Visit https://example.com.").endswith("https://example.com.")


def test_accepts_message_at_200_characters():
    padded = MESSAGE + "x" * (200 - len(MESSAGE))
    assert len(validate_message(padded)) == 200


def test_publishes_to_all_platforms():
    response = publish()

    assert response.success is True
    assert [result.platform for result in response.results] == [
        "Bluesky",
        "Mastodon",
        "Dev.to",
        "WordPress",
        "Hugging Face",
    ]
    assert all(result.status == "success" for result in response.results)
    assert all(result.public_access for result in response.results)
    assert all(result.error is None for result in response.results)
    assert response.results[0].posted_url == "https://bsky.app/profile/tester.bsky.social/post/xyz123"
    assert response.results[1].posted_url == "https://mastodon.online/@tester/1"
    assert len(response.results[2].date) == 10 and len(response.results[2].time) == 8


def test_one_failure_does_not_stop_other_platforms():
    def flaky(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/api/articles"):
            return httpx.Response(500, text="internal failure " * 100)
        return handler(request)

    response = publish(flaky)

    assert response.success is True
    failed = response.results[2]
    assert failed.platform == "Dev.to"
    assert failed.status == "failed"
    assert failed.posted_url is None
    assert failed.public_access is False
    assert failed.date is None and failed.time is None
    assert failed.error.startswith("HTTP 500")
    assert len(failed.error) <= 300
    assert all(result.status == "success" for result in response.results[:2] + response.results[3:])


def test_all_missing_credentials_returns_failed_results(monkeypatch):
    for field in CREDENTIALS:
        monkeypatch.setattr(settings, field, None)

    response = TestClient(app).post("/posting", json={"message": MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert len(body["results"]) == 5
    assert all(result["status"] == "failed" for result in body["results"])
    assert "missing credentials: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD" == body["results"][0]["error"]
