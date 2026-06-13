import logging
from dataclasses import dataclass
from uuid import UUID

import httpx

from app.config import Settings, get_settings
from app.services.telegram_common import build_public_news_url, excerpt_html, telegram_api_post

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramDeliveryResult:
    sent: bool
    skipped: bool = False
    error: str | None = None
    message_id: int | None = None


class TelegramPublishBot:
    """Bot 1: сайт/админка → чат СНТ в Telegram."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def is_enabled(self) -> bool:
        return bool(
            self._settings.telegram_publish_enabled
            and self._settings.telegram_publish_bot_token
            and self._settings.telegram_publish_chat_id
        )

    def build_news_url(self, news_id: UUID) -> str:
        return build_public_news_url(self._settings, news_id)

    async def send_important_news(
        self,
        *,
        news_id: UUID,
        title: str,
        content_html: str,
    ) -> TelegramDeliveryResult:
        if not self._settings.telegram_publish_enabled:
            return TelegramDeliveryResult(sent=False, skipped=True, error="publish_disabled")

        token = self._settings.telegram_publish_bot_token
        chat_id = self._settings.telegram_publish_chat_id
        if not token or not chat_id:
            return TelegramDeliveryResult(sent=False, skipped=True, error="publish_not_configured")

        news_url = self.build_news_url(news_id)
        summary = excerpt_html(content_html, length=280)
        text = (
            "📢 Важное объявление ТСН «ДОНИ»\n\n"
            f"{title.strip()}\n\n"
            f"{summary}\n\n"
            f"Подробнее: {news_url}"
        )

        try:
            body = await telegram_api_post(
                token,
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": False,
                },
            )
        except httpx.HTTPError as exc:
            logger.warning("Publish bot failed for news %s: %s", news_id, exc)
            return TelegramDeliveryResult(sent=False, error=str(exc))

        message_id = (body.get("result") or {}).get("message_id")
        logger.info("Publish bot sent news %s (message_id=%s)", news_id, message_id)
        return TelegramDeliveryResult(sent=True, message_id=message_id)


def get_telegram_publish_bot() -> TelegramPublishBot:
    return TelegramPublishBot()
