from datetime import datetime, timezone

from app.config import settings
from app.platforms.base import AdapterResult, PlatformAdapter, api_error


class BlueskyAdapter(PlatformAdapter):
    name = "Bluesky"
    credential_names = ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD")

    async def post(self, text: str) -> AdapterResult:
        base = settings.bluesky_pds_url.rstrip("/")
        session = await self.client.post(
            f"{base}/xrpc/com.atproto.server.createSession",
            json={
                "identifier": settings.bluesky_handle,
                "password": settings.bluesky_app_password,
            },
        )
        if session.is_error:
            raise RuntimeError(api_error(session))
        auth = session.json()

        created = await self.client.post(
            f"{base}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {auth['accessJwt']}"},
            json={
                "repo": auth["did"],
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                },
            },
        )
        if created.is_error:
            raise RuntimeError(api_error(created))

        rkey = created.json()["uri"].rsplit("/", 1)[-1]
        handle = auth.get("handle") or settings.bluesky_handle
        return AdapterResult(f"https://bsky.app/profile/{handle}/post/{rkey}", True)
