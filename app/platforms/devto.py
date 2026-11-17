from app.config import settings
from app.platforms.base import AdapterResult, PlatformAdapter, api_error, derive_title


class DevToAdapter(PlatformAdapter):
    name = "Dev.to"
    credential_names = ("DEVTO_API_KEY",)

    async def post(self, text: str) -> AdapterResult:
        response = await self.client.post(
            "https://dev.to/api/articles",
            headers={
                "api-key": settings.devto_api_key,
                "accept": "application/vnd.forem.api-v1+json",
                "user-agent": "automated-posting/0.1",
            },
            json={
                "article": {
                    "title": derive_title(text),
                    "body_markdown": text,
                    "published": True,
                }
            },
        )
        if response.is_error:
            raise RuntimeError(api_error(response))
        data = response.json()
        return AdapterResult(data.get("url"), True)
