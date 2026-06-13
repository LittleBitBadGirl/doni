from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InfrastructurePage
from app.templating import INFRASTRUCTURE_SLUGS, base_context, templates

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


@router.get("")
async def infrastructure_index() -> RedirectResponse:
    return RedirectResponse(url="/infrastructure/gas", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/{slug}", response_class=HTMLResponse)
async def infrastructure_detail(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    if slug not in INFRASTRUCTURE_SLUGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден")

    page = await db.scalar(select(InfrastructurePage).where(InfrastructurePage.slug == slug))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден")

    all_pages = (
        await db.scalars(
            select(InfrastructurePage)
            .where(InfrastructurePage.slug.in_(INFRASTRUCTURE_SLUGS))
            .order_by(InfrastructurePage.slug)
        )
    ).all()

    nav_pages = sorted(
        all_pages,
        key=lambda p: INFRASTRUCTURE_SLUGS.index(p.slug) if p.slug in INFRASTRUCTURE_SLUGS else 999,
    )

    return templates.TemplateResponse(
        request=request,
        name="infrastructure/detail.html",
        context={
            **base_context(),
            "title": page.title,
            "page": page,
            "nav_pages": nav_pages,
            "active_slug": slug,
        },
    )
