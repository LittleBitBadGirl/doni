from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, News
from app.templating import base_context, templates

router = APIRouter(tags=["pages"])

NEWS_PREVIEW_LIMIT = 5


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    pinned_news = (
        await db.scalars(
            select(News)
            .where(News.is_pinned.is_(True))
            .order_by(News.published_at.desc())
        )
    ).all()

    recent_news = (
        await db.scalars(
            select(News)
            .where(News.is_pinned.is_(False))
            .order_by(News.published_at.desc())
            .limit(NEWS_PREVIEW_LIMIT)
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            **base_context(),
            "title": "Главная",
            "pinned_news": pinned_news,
            "recent_news": recent_news,
        },
    )


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = Query(default=""),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="search/index.html",
        context={
            **base_context(),
            "title": "Поиск",
            "query": q.strip(),
        },
    )


@router.get("/search/results", response_class=HTMLResponse)
async def search_results(
    request: Request,
    q: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    query = q.strip()
    news_items: list[News] = []
    documents: list[Document] = []

    if len(query) >= 2:
        pattern = f"%{query}%"
        news_items = (
            await db.scalars(
                select(News)
                .where(or_(News.title.ilike(pattern), News.content.ilike(pattern)))
                .order_by(News.published_at.desc())
                .limit(20)
            )
        ).all()
        documents = (
            await db.scalars(
                select(Document)
                .where(Document.title.ilike(pattern))
                .order_by(Document.created_at.desc())
                .limit(20)
            )
        ).all()

    return templates.TemplateResponse(
        request=request,
        name="search/_results.html",
        context={
            "query": query,
            "news_items": news_items,
            "documents": documents,
        },
    )
