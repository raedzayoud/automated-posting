import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def _clean_link(raw: str) -> str:
    link = raw.rstrip(".,;:!?'\"")
    while link.endswith(")") and link.count("(") < link.count(")"):
        link = link[:-1]
    return link


def validate_message(message: str) -> str:
    message = message.strip()
    if not message:
        raise ValueError("Message must not be empty.")
    if len(message) > 200:
        raise ValueError("Message must be at most 200 characters.")

    links = [_clean_link(match) for match in URL_PATTERN.findall(message)]
    if not links:
        raise ValueError("Message must contain exactly one CTA link.")
    if len(links) > 1:
        raise ValueError(f"Message must contain exactly one CTA link, found {len(links)}.")

    parsed = urlparse(links[0])
    if parsed.scheme not in ("http", "https") or "." not in parsed.netloc:
        raise ValueError("The CTA link must be a valid http(s) URL.")
    return message


class PostingRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        return validate_message(value)


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
