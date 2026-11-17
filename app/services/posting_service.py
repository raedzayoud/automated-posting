import asyncio
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter
from app.schemas import PlatformResult, PostingResponse


class PostingService:
    def __init__(self, adapters: list[PlatformAdapter], timeout: float | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self._adapters = list(adapters)
        self._timeout = timeout if timeout is not None else settings.post_timeout_seconds
        self._transport = transport

    async def publish(self, message: str) -> PostingResponse:
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            for adapter in self._adapters:
                adapter.client = client
            results = await asyncio.gather(*(self._run(adapter, message) for adapter in self._adapters))
        return PostingResponse(
            success=any(result.status == "success" for result in results),
            results=list(results),
        )

    async def _run(self, adapter: PlatformAdapter, message: str) -> PlatformResult:
        if not adapter.enabled:
            return PlatformResult(
                platform=adapter.name,
                status="failed",
                error=f"missing credentials: {', '.join(adapter.missing_credentials)}",
            )
        try:
            posted = await adapter.post(message)
        except Exception as exc:
            return PlatformResult(platform=adapter.name, status="failed", error=_clean_error(exc))

        now = datetime.now(timezone.utc)
        return PlatformResult(
            platform=adapter.name,
            status="success",
            posted_url=posted.url,
            public_access=posted.public_access,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
        )


def _clean_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:300] or exc.__class__.__name__
