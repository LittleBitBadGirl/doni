import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette_csrf import CSRFMiddleware

from app.admin import setup_admin
from app.config import get_settings
from app.database import engine
from app.limiter import limiter
from app.routers.auth import router as auth_router
from app.routers.contacts import router as contacts_router
from app.routers.documents import router as documents_router
from app.routers.finance import router as finance_router
from app.routers.infrastructure import router as infrastructure_router
from app.routers.news import router as news_router
from app.routers.pages import router as pages_router
from app.routers.telegram_inlet import router as telegram_inlet_router
from app.services.telegram_inlet import get_telegram_inlet_bot

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


async def _telegram_inlet_polling_loop(stop_event: asyncio.Event) -> None:
    bot = get_telegram_inlet_bot()
    while not stop_event.is_set():
        try:
            await bot.poll_once()
        except Exception:
            logger.exception("Inlet bot polling failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    stop_event = asyncio.Event()
    polling_task: asyncio.Task | None = None
    inlet_bot = get_telegram_inlet_bot()

    if inlet_bot.is_enabled:
        if settings.telegram_inlet_use_polling:
            polling_task = asyncio.create_task(_telegram_inlet_polling_loop(stop_event))
            logger.info("Inlet bot polling started")
        else:
            try:
                await inlet_bot.register_webhook()
            except Exception:
                logger.exception("Failed to register inlet bot webhook")

    yield

    stop_event.set()
    if polling_task is not None:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()


app = FastAPI(
    title="ТСН «ДОНИ»",
    description="Информационный портал ТСН «ДОНИ»",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(pages_router)
app.include_router(news_router)
app.include_router(documents_router)
app.include_router(finance_router)
app.include_router(infrastructure_router)
app.include_router(contacts_router)
app.include_router(auth_router)
app.include_router(telegram_inlet_router)
setup_admin(app)

app.add_middleware(
    CSRFMiddleware,
    secret=settings.secret_key,
    cookie_secure=settings.app_env == "production",
    cookie_samesite="strict",
    sensitive_cookies={"admin_token"},
    required_urls=[
        re.compile(r"^/admin/login$"),
        re.compile(r"^/documents/upload$"),
        re.compile(r"^/finance/debtors/upload$"),
    ],
    exempt_urls=[
        re.compile(r"^/health$"),
        re.compile(r"^/api/telegram/inlet/.*$"),
    ],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
