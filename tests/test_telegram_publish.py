"""Unit tests for Telegram publish bot."""

from uuid import uuid4

import httpx
import pytest
import respx

from app.config import Settings
from app.services.telegram_publish import TelegramPublishBot


class TestTelegramPublishBot:
    def test_should_be_disabled_by_default(self):
        bot = TelegramPublishBot(settings=Settings())
        assert bot.is_enabled is False

    @respx.mock
    async def test_should_send_message_when_enabled(self):
        news_id = uuid4()
        settings = Settings(
            telegram_publish_enabled=True,
            telegram_publish_bot_token="123456:PUB",
            telegram_publish_chat_id="-100123",
            public_site_url="https://tsndoni.ru",
        )
        bot = TelegramPublishBot(settings=settings)

        respx.post("https://api.telegram.org/bot123456:PUB/sendMessage").mock(
            return_value=respx.MockResponse(
                200,
                json={"ok": True, "result": {"message_id": 42}},
            )
        )

        result = await bot.send_important_news(
            news_id=news_id,
            title="Важное объявление",
            content_html="<p>Текст новости</p>",
        )

        assert result.sent is True
        assert result.message_id == 42
        import json

        payload = json.loads(respx.calls.last.request.content)
        assert "Важное объявление" in payload["text"]
        assert str(news_id) in payload["text"]

    async def test_should_skip_when_disabled(self):
        bot = TelegramPublishBot(settings=Settings(telegram_publish_enabled=False))

        result = await bot.send_important_news(
            news_id=uuid4(),
            title="Test",
            content_html="<p>x</p>",
        )

        assert result.sent is False
        assert result.skipped is True

    @respx.mock
    async def test_should_return_error_on_api_failure(self):
        settings = Settings(
            telegram_publish_enabled=True,
            telegram_publish_bot_token="123456:PUB",
            telegram_publish_chat_id="-100123",
        )
        bot = TelegramPublishBot(settings=settings)

        respx.post("https://api.telegram.org/bot123456:PUB/sendMessage").mock(
            return_value=respx.MockResponse(200, json={"ok": False, "description": "blocked"})
        )

        result = await bot.send_important_news(
            news_id=uuid4(),
            title="Test",
            content_html="<p>x</p>",
        )

        assert result.sent is False
        assert result.error is not None
