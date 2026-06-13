"""Shared pytest fixtures for tsndoni."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Env must be set before any app imports that read Settings / create engine.
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://tsndoni:tsndoni@localhost:5432/tsndoni_test",
    ),
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TELEGRAM_INLET_ENABLED", "false")
os.environ.setdefault("TELEGRAM_INLET_USE_POLLING", "false")
os.environ.setdefault("TELEGRAM_PUBLISH_ENABLED", "false")


def _clear_settings_cache() -> None:
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def db_engine():
    """Fresh PostgreSQL schema per test; skips if DB is unavailable."""
    _clear_settings_cache()

    from app.config import get_settings
    from app.database import Base

    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable ({settings.database_url}): {exc}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    from app.auth.password import hash_password
    from app.models import AdminUser

    admin = AdminUser(
        id=uuid4(),
        email="admin@tsndoni.ru",
        password_hash=hash_password("changeme"),
        full_name="Test Admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.database import get_db
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_settings(monkeypatch):
    """Fresh Settings with telegram inlet enabled for webhook tests."""
    monkeypatch.setenv("TELEGRAM_INLET_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_INLET_BOT_TOKEN", "123456:TEST")
    monkeypatch.setenv("TELEGRAM_INLET_WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("TELEGRAM_INLET_ALLOWED_USER_IDS", "111,222")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost:8080")
    _clear_settings_cache()
    yield
    _clear_settings_cache()
