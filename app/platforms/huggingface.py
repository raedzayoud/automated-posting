from app.config import settings
from app.platforms.base import AdapterResult, PlatformAdapter, api_error, derive_title


class HuggingFaceAdapter(PlatformAdapter):
    name = "Hugging Face"
    credential_names = ("HF_TOKEN", "HF_REPO")

    async def post(self, text: str) -> AdapterResult:
        repo = settings.hf_repo.strip("/")
        response = await self.client.post(
            f"https://huggingface.co/api/models/{repo}/discussions",
            headers={"Authorization": f"Bearer {settings.hf_token}"},
            json={"title": derive_title(text, limit=200), "description": text},
        )
        if response.is_error:
            raise RuntimeError(api_error(response))
        data = response.json()
        url = data.get("url") or f"https://huggingface.co/{repo}/discussions/{data.get('num')}"
        return AdapterResult(url, True)
