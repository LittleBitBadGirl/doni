"""Unit tests for Telegram inlet bot logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import respx

from app.config import Settings
from app.models import AdminUser, NewsSource
from app.services.telegram_inlet import TelegramInletBot


@pytest.fixture
def inlet_bot() -> TelegramInletBot:
    settings = Settings(
        telegram_inlet_enabled=True,
        telegram_inlet_bot_token="123456:TEST",
        telegram_inlet_allowed_user_ids="42",
        telegram_inlet_webhook_secret="wh-secret",
        public_site_url="http://localhost:8080",
    )
    return TelegramInletBot(settings=settings)


class TestTelegramInletBotConfig:
    def test_should_be_enabled_when_configured(self, inlet_bot):
        assert inlet_bot.is_enabled is True

    def test_should_be_disabled_without_whitelist(self):
        bot = TelegramInletBot(
            settings=Settings(
                telegram_inlet_enabled=True,
                telegram_inlet_bot_token="123456:TEST",
                telegram_inlet_allowed_user_ids="",
            )
        )
        assert bot.is_enabled is False

    def test_should_check_user_whitelist(self, inlet_bot):
        assert inlet_bot.is_user_allowed(42) is True
        assert inlet_bot.is_user_allowed(99) is False
        assert inlet_bot.is_user_allowed(None) is False

    def test_should_build_webhook_url(self, inlet_bot):
        assert inlet_bot.webhook_path() == "/api/telegram/inlet/wh-secret"
        assert inlet_bot.webhook_url() == "http://localhost:8080/api/telegram/inlet/wh-secret"


class TestCreateImportantNews:
    async def test_should_create_pinned_news_from_telegram(self, db_session, admin_user):
        bot = TelegramInletBot(
            settings=Settings(
                telegram_inlet_enabled=True,
                telegram_inlet_bot_token="123456:TEST",
                telegram_inlet_allowed_user_ids="1",
            )
        )

        result = await bot.create_important_news(
            db_session,
            text="Заголовок\nТекст",
            telegram_user_id=1,
        )

        assert result.created is True
        assert result.news_id is not None

        from sqlalchemy import select

        from app.models import News

        news = await db_session.scalar(select(News).where(News.id == result.news_id))
        assert news is not None
        assert news.title == "Заголовок"
        assert news.is_pinned is True
        assert news.source == NewsSource.telegram_inlet
        assert news.created_by_id == admin_user.id

    async def test_should_fail_when_no_active_admin(self, db_session):
        bot = TelegramInletBot(
            settings=Settings(
                telegram_inlet_enabled=True,
                telegram_inlet_bot_token="123456:TEST",
                telegram_inlet_allowed_user_ids="1",
            )
        )

        result = await bot.create_important_news(
            db_session,
            text="Заголовок\nТекст",
            telegram_user_id=1,
        )

        assert result.created is False
        assert result.error == "no_active_admin"

    async def test_should_fail_on_empty_message(self, db_session, admin_user):
        bot = TelegramInletBot(settings=Settings(telegram_inlet_allowed_user_ids="1"))

        result = await bot.create_important_news(
            db_session,
            text="   ",
            telegram_user_id=1,
        )

        assert result.created is False
        assert result.error == "empty_message"


class TestHandleUpdate:
    @respx.mock
    async def test_should_reply_with_whoami(self, inlet_bot):
        respx.post("https://api.telegram.org/bot123456:TEST/sendMessage").mock(
            return_value=respx.MockResponse(200, json={"ok": True, "result": {"message_id": 1}})
        )

        await inlet_bot.handle_update(
            {
                "message": {
                    "from": {"id": 42},
                    "chat": {"id": 100},
                    "text": "/whoami",
                }
            }
        )

        assert respx.calls.call_count == 1
        assert "42" in respx.calls.last.request.content.decode()

    @respx.mock
    async def test_should_deny_unlisted_user(self, inlet_bot):
        respx.post("https://api.telegram.org/bot123456:TEST/sendMessage").mock(
            return_value=respx.MockResponse(200, json={"ok": True, "result": {"message_id": 1}})
        )

        with patch.object(inlet_bot, "create_important_news", new_callable=AsyncMock) as mock_create:
            await inlet_bot.handle_update(
                {
                    "message": {
                        "from": {"id": 999},
                        "chat": {"id": 100},
                        "text": "Заголовок\nТекст",
                    }
                }
            )

        mock_create.assert_not_called()
        assert respx.calls.call_count == 1
        import json

        payload = json.loads(respx.calls.last.request.content)
        assert "Нет доступа" in payload["text"]
