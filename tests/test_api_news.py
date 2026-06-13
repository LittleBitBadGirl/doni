"""Integration tests for public news pages."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models import News, NewsSource


@pytest.mark.asyncio
async def test_should_list_important_news(client, db_session, admin_user):
    news = News(
        id=uuid4(),
        title="Срочное объявление",
        content="<p>Текст</p>",
        is_pinned=True,
        source=NewsSource.telegram_inlet,
        published_at=datetime.now(timezone.utc),
        created_by_id=admin_user.id,
    )
    db_session.add(news)
    await db_session.commit()

    response = await client.get("/news/important")

    assert response.status_code == 200
    assert "Срочное объявление" in response.text


@pytest.mark.asyncio
async def test_should_return_404_for_missing_news(client):
    response = await client.get(f"/news/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_should_render_home_page(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert "ДОНИ" in response.text or "Главная" in response.text
