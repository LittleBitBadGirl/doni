from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models import AuditAction, FinanceInfo
from app.services.audit import write_audit_log
from app.services.storage import (
    DEBTORS_ALLOWED_EXTENSIONS,
    StorageValidationError,
    delete_stored_file,
    file_exists,
    resolve_stored_path,
    save_bytes,
)
from app.templating import base_context, templates

router = APIRouter(tags=["finance"])


@router.get("/admin/finance/debtors/upload", response_class=HTMLResponse)
async def upload_debtors_page(
    request: Request,
    admin_id: UUID = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    finance = await _get_current_finance(db)
    current_file = finance.debtors_filename if finance else None
    current_available = bool(current_file and file_exists(current_file))

    return templates.TemplateResponse(
        request=request,
        name="admin/upload_debtors.html",
        context={
            **base_context(),
            "title": "Загрузка списка должников",
            "error": None,
            "current_file": current_file,
            "current_available": current_available,
        },
    )


@router.post("/finance/debtors/upload", response_model=None)
async def upload_debtors_list(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin_id: UUID = Depends(require_admin),
):
    finance = await _get_current_finance(db)
    if finance is None:
        return _debtors_form_error(request, None, "Сначала создайте запись «Финансы» в админ-панели.")

    if not file.filename:
        return _debtors_form_error(request, finance, "Выберите файл для загрузки.")

    content = await file.read()
    try:
        stored_filename, mime_type, file_size = save_bytes(
            content,
            category="finance",
            original_filename=file.filename,
            content_type=file.content_type,
            allowed_extensions=DEBTORS_ALLOWED_EXTENSIONS,
        )
    except StorageValidationError as exc:
        return _debtors_form_error(request, finance, str(exc))

    old_filename = finance.debtors_filename
    finance.debtors_filename = stored_filename
    finance.updated_by_id = admin_id

    await write_audit_log(
        db,
        action=AuditAction.finance_updated,
        request=request,
        admin_user_id=admin_id,
        metadata={
            "action": "debtors_upload",
            "stored_filename": stored_filename,
            "mime_type": mime_type,
            "file_size_bytes": file_size,
            "replaced": old_filename,
        },
    )
    await db.commit()

    if old_filename and old_filename != stored_filename:
        delete_stored_file(old_filename)

    return RedirectResponse(
        url="/admin/finance/debtors/upload?success=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _debtors_form_error(
    request: Request,
    finance: FinanceInfo | None,
    error: str,
) -> HTMLResponse:
    current_file = finance.debtors_filename if finance else None
    current_available = bool(current_file and file_exists(current_file))

    return templates.TemplateResponse(
        request=request,
        name="admin/upload_debtors.html",
        context={
            **base_context(),
            "title": "Загрузка списка должников",
            "error": error,
            "current_file": current_file,
            "current_available": current_available,
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )


async def _get_current_finance(db: AsyncSession) -> FinanceInfo | None:
    return await db.scalar(
        select(FinanceInfo)
        .where(FinanceInfo.is_current.is_(True))
        .order_by(FinanceInfo.updated_at.desc())
        .limit(1)
    )


@router.get("/finance", response_class=HTMLResponse)
async def finance_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    finance = await _get_current_finance(db)

    debtors_available = False
    if finance and finance.debtors_filename:
        debtors_available = file_exists(finance.debtors_filename)

    return templates.TemplateResponse(
        request=request,
        name="finance/index.html",
        context={
            **base_context(),
            "title": "Финансы",
            "finance": finance,
            "debtors_available": debtors_available,
        },
    )


@router.get("/finance/debtors")
async def download_debtors_list(
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    finance = await _get_current_finance(db)
    if finance is None or not finance.debtors_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Список должников пока не опубликован.",
        )

    if not file_exists(finance.debtors_filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл списка должников ещё не загружен на сервер.",
        )

    file_path = resolve_stored_path(finance.debtors_filename)
    original_name = Path(finance.debtors_filename).name
    media_type = "application/pdf" if original_name.lower().endswith(".pdf") else "text/csv"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=original_name,
    )
