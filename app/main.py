from fastapi import FastAPI

from app.config import settings
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.huggingface import HuggingFaceAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.wordpress import WordPressAdapter
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

app = FastAPI(title=settings.app_name)


def build_adapters():
    return [
        BlueskyAdapter(),
        MastodonAdapter(),
        DevToAdapter(),
        WordPressAdapter(),
        HuggingFaceAdapter(),
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/posting", response_model=PostingResponse)
async def posting(request: PostingRequest) -> PostingResponse:
    return await PostingService(build_adapters()).publish(request.message)
