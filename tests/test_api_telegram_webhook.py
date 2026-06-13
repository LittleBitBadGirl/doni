"""Integration tests for Telegram inlet webhook."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_should_reject_webhook_when_disabled(client):
    response = await client.post(
        "/api/telegram/inlet/any-secret",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "any-secret"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_should_accept_valid_webhook(test_settings, client):
    payload = {
        "update_id": 1,
        "message": {
            "from": {"id": 111},
            "chat": {"id": 111},
            "text": "/help",
        },
    }

    with patch(
        "app.routers.telegram_inlet.get_telegram_inlet_bot"
    ) as mock_get_bot:
        mock_bot = AsyncMock()
        mock_get_bot.return_value = mock_bot

        response = await client.post(
            "/api/telegram/inlet/test-webhook-secret",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_bot.handle_update.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_should_reject_invalid_secret_token(test_settings, client):
    response = await client.post(
        "/api/telegram/inlet/test-webhook-secret",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_should_reject_unknown_webhook_path(test_settings, client):
    response = await client.post(
        "/api/telegram/inlet/wrong-path",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )

    assert response.status_code == 404
