from app.config import settings
from app.platforms.base import AdapterResult, PlatformAdapter, api_error, derive_title


class WordPressAdapter(PlatformAdapter):
    name = "WordPress"
    credential_names = ("WORDPRESS_SITE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD")

    async def post(self, text: str) -> AdapterResult:
        response = await self.client.post(
            f"{settings.wordpress_site_url.rstrip('/')}/wp-json/wp/v2/posts",
            auth=(settings.wordpress_username, settings.wordpress_app_password),
            json={
                "title": derive_title(text),
                "content": text,
                "status": "publish",
            },
        )
        if response.is_error:
            raise RuntimeError(api_error(response))
        data = response.json()
        return AdapterResult(data.get("link"), data.get("status") == "publish")
