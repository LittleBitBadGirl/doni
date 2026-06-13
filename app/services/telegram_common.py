import html
import logging
import re
from uuid import UUID

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_TAG_RE = re.compile(r"<[^>]+>")


def excerpt_html(html_content: str, length: int = 280) -> str:
    text = _TAG_RE.sub("", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rsplit(" ", 1)[0] + "…"


def plain_text_to_html(text: str) -> str:
    blocks = [block.strip() for block in text.strip().split("\n\n") if block.strip()]
    if not blocks:
        blocks = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not blocks:
        return "<p></p>"
    return "".join(f"<p>{html.escape(block.replace(chr(10), ' '))}</p>" for block in blocks)


def parse_title_and_body(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty_message")

    title = lines[0][:500]
    if len(lines) == 1:
        return title, title

    body = "\n".join(lines[1:]).strip()
    if not body:
        body = title
    return title, body


def build_public_news_url(settings: Settings, news_id: UUID) -> str:
    base_url = settings.public_site_url.rstrip("/")
    path = f"/news/{news_id}"
    if not base_url:
        return path
    return f"{base_url}{path}"


async def telegram_api_post(token: str, method: str, payload: dict) -> dict:
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        body = response.json()
    if not body.get("ok"):
        description = str(body.get("description") or "telegram_api_error")
        logger.warning("Telegram API %s failed: %s", method, description)
        raise httpx.HTTPError(description)
    return body
