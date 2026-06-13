from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ContactInfo
from app.templating import base_context, templates

router = APIRouter(tags=["contacts"])


async def _get_contact_info(db: AsyncSession) -> ContactInfo | None:
    return await db.scalar(
        select(ContactInfo).order_by(ContactInfo.updated_at.desc()).limit(1)
    )


@router.get("/contacts", response_class=HTMLResponse)
async def contacts_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    contact = await _get_contact_info(db)

    return templates.TemplateResponse(
        request=request,
        name="contacts.html",
        context={
            **base_context(),
            "title": "Контакты",
            "contact": contact,
        },
    )
