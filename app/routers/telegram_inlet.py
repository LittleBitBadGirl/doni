"""Telegram inlet webhook (Bot 2)."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.services.telegram_inlet import get_telegram_inlet_bot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/inlet/{webhook_secret}")
async def telegram_inlet_webhook(webhook_secret: str, request: Request) -> dict[str, bool]:
    settings = get_settings()
    bot = get_telegram_inlet_bot()

    if not settings.telegram_inlet_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    expected_secret = settings.telegram_inlet_webhook_secret.strip()
    if not expected_secret or webhook_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    try:
        update = await request.json()
    except Exception as exc:
        logger.warning("Invalid Telegram webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc

    await bot.handle_update(update)
    return {"ok": True}
