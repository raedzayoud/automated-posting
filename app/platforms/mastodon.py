from app.config import settings
from app.platforms.base import AdapterResult, PlatformAdapter, api_error


class MastodonAdapter(PlatformAdapter):
    name = "Mastodon"
    credential_names = ("MASTODON_BASE_URL", "MASTODON_ACCESS_TOKEN")

    async def post(self, text: str) -> AdapterResult:
        response = await self.client.post(
            f"{settings.mastodon_base_url.rstrip('/')}/api/v1/statuses",
            headers={"Authorization": f"Bearer {settings.mastodon_access_token}"},
            json={"status": text, "visibility": "public"},
        )
        if response.is_error:
            raise RuntimeError(api_error(response))
        data = response.json()
        return AdapterResult(data.get("url") or data.get("uri"), data.get("visibility") == "public")
