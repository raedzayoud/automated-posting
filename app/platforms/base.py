from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class AdapterResult:
    url: str | None
    public_access: bool


def api_error(response: httpx.Response) -> str:
    body = " ".join(response.text.split())
    return f"HTTP {response.status_code}: {body[:200]}"


def derive_title(text: str, limit: int = 60) -> str:
    head = text.split("http", 1)[0].strip(" -\u2013\u2014:,.")
    if len(head) < 3:
        head = "New update"
    return head[:limit].rstrip(" -\u2013\u2014:,.")


class PlatformAdapter(ABC):
    name: str
    credential_names: tuple[str, ...] = ()

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client

    @property
    def missing_credentials(self) -> list[str]:
        return [name for name in self.credential_names if not getattr(settings, name.lower(), None)]

    @property
    def enabled(self) -> bool:
        return not self.missing_credentials

    @abstractmethod
    async def post(self, text: str) -> AdapterResult:
        """Publish text and return its public URL and whether it is publicly reachable."""
