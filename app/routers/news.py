import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import News
from app.templating import base_context, templates

router = APIRouter(prefix="/news", tags=["news"])

PAGE_SIZE = 10


@router.get("/important", response_class=HTMLResponse)
async def important_news_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    total = await db.scalar(
        select(func.count()).select_from(News).where(News.is_pinned.is_(True))
    ) or 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    news_items = (
        await db.scalars(
            select(News)
            .where(News.is_pinned.is_(True))
            .order_by(News.published_at.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="news/important.html",
        context={
            **base_context(),
            "title": "Важно!",
            "news_items": news_items,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("", response_class=HTMLResponse)
async def news_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    total = await db.scalar(select(func.count()).select_from(News)) or 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    news_items = (
        await db.scalars(
            select(News)
            .order_by(News.is_pinned.desc(), News.published_at.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="news/list.html",
        context={
            **base_context(),
            "title": "Новости",
            "news_items": news_items,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/{news_id}", response_class=HTMLResponse)
async def news_detail(
    request: Request,
    news_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    news_item = await db.get(News, news_id)
    if news_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Новость не найдена")

    return templates.TemplateResponse(
        request=request,
        name="news/detail.html",
        context={
            **base_context(),
            "title": news_item.title,
            "news_item": news_item,
        },
    )
