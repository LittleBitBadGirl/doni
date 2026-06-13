import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import async_session_factory
from app.models import AdminUser, News, NewsSource
from app.services.telegram_common import (
    build_public_news_url,
    parse_title_and_body,
    plain_text_to_html,
    telegram_api_post,
)

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Бот публикации важных объявлений на сайте ТСН «ДОНИ».\n\n"
    "Формат сообщения:\n"
    "• первая строка — заголовок\n"
    "• остальные строки — текст объявления\n\n"
    "Команды:\n"
    "/whoami — ваш Telegram ID (для whitelist)\n"
    "/help — эта справка"
)


@dataclass(frozen=True)
class InletPublishResult:
    created: bool
    news_id: UUID | None = None
    error: str | None = None


class TelegramInletBot:
    """Bot 2: Telegram → сайт (раздел «Важно!»)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._poll_offset: int | None = None

    @property
    def is_enabled(self) -> bool:
        return bool(
            self._settings.telegram_inlet_enabled
            and self._settings.telegram_inlet_bot_token
            and self._settings.telegram_inlet_allowed_user_ids
        )

    def is_user_allowed(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return user_id in self._settings.parsed_inlet_allowed_user_ids

    def webhook_path(self) -> str:
        secret = self._settings.telegram_inlet_webhook_secret.strip()
        if not secret:
            raise ValueError("telegram_inlet_webhook_secret is required")
        return f"/api/telegram/inlet/{secret}"

    def webhook_url(self) -> str:
        return f"{self._settings.public_site_url.rstrip('/')}{self.webhook_path()}"

    async def register_webhook(self) -> None:
        if not self.is_enabled:
            return

        await telegram_api_post(
            self._settings.telegram_inlet_bot_token,
            "setWebhook",
            {
                "url": self.webhook_url(),
                "secret_token": self._settings.telegram_inlet_webhook_secret,
                "allowed_updates": ["message"],
                "drop_pending_updates": True,
            },
        )
        logger.info("Inlet bot webhook registered at %s", self.webhook_url())

    async def delete_webhook(self) -> None:
        if not self._settings.telegram_inlet_bot_token:
            return
        await telegram_api_post(
            self._settings.telegram_inlet_bot_token,
            "deleteWebhook",
            {"drop_pending_updates": True},
        )

    async def poll_once(self) -> None:
        if not self.is_enabled:
            return

        payload: dict = {"timeout": 0, "allowed_updates": ["message"]}
        if self._poll_offset is not None:
            payload["offset"] = self._poll_offset

        body = await telegram_api_post(
            self._settings.telegram_inlet_bot_token,
            "getUpdates",
            payload,
        )
        for update in body.get("result") or []:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._poll_offset = update_id + 1
            await self.handle_update(update)

    async def handle_update(self, update: dict) -> None:
        message = update.get("message")
        if not message:
            return

        from_user = message.get("from") or {}
        user_id = from_user.get("id")
        chat_id = (message.get("chat") or {}).get("id")
        text = (message.get("text") or "").strip()

        if chat_id is None or not text:
            return

        if text.startswith("/"):
            await self._handle_command(chat_id=chat_id, user_id=user_id, text=text)
            return

        if not self.is_user_allowed(user_id):
            await self._reply(
                chat_id,
                "Нет доступа. Обратитесь к администратору сайта и передайте ваш Telegram ID "
                "(команда /whoami).",
            )
            return

        async with async_session_factory() as session:
            result = await self.create_important_news(session, text=text, telegram_user_id=user_id)

        if result.created and result.news_id:
            url = build_public_news_url(self._settings, result.news_id)
            await self._reply(chat_id, f"✅ Опубликовано в разделе «Важно!» на сайте.\n\n{url}")
        else:
            await self._reply(chat_id, f"Не удалось опубликовать: {result.error or 'unknown_error'}")

    async def _handle_command(self, *, chat_id: int, user_id: int | None, text: str) -> None:
        command = text.split()[0].split("@")[0].lower()
        if command in {"/start", "/help"}:
            await self._reply(chat_id, HELP_TEXT)
            return
        if command == "/whoami":
            await self._reply(chat_id, f"Ваш Telegram ID: {user_id}\n\nПередайте его администратору сайта.")
            return
        await self._reply(chat_id, "Неизвестная команда. Используйте /help.")

    async def create_important_news(
        self,
        session: AsyncSession,
        *,
        text: str,
        telegram_user_id: int | None,
    ) -> InletPublishResult:
        try:
            title, body = parse_title_and_body(text)
        except ValueError:
            return InletPublishResult(created=False, error="empty_message")

        admin = await session.scalar(
            select(AdminUser)
            .where(AdminUser.is_active.is_(True))
            .order_by(AdminUser.created_at.asc())
            .limit(1)
        )
        if admin is None:
            return InletPublishResult(created=False, error="no_active_admin")

        news = News(
            title=title,
            content=plain_text_to_html(body),
            is_pinned=True,
            published_at=datetime.now(timezone.utc),
            created_by_id=admin.id,
            source=NewsSource.telegram_inlet,
        )
        session.add(news)
        await session.commit()
        await session.refresh(news)

        logger.info(
            "Inlet bot created important news %s from telegram user %s",
            news.id,
            telegram_user_id,
        )
        return InletPublishResult(created=True, news_id=news.id)

    async def _reply(self, chat_id: int, text: str) -> None:
        if not self._settings.telegram_inlet_bot_token:
            return
        try:
            await telegram_api_post(
                self._settings.telegram_inlet_bot_token,
                "sendMessage",
                {"chat_id": chat_id, "text": text},
            )
        except httpx.HTTPError as exc:
            logger.warning("Inlet bot failed to reply in chat %s: %s", chat_id, exc)


def get_telegram_inlet_bot() -> TelegramInletBot:
    return TelegramInletBot()
