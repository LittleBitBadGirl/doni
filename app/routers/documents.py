import uuid
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models import AuditAction, Document
from app.models.document import DocumentCategory
from app.services.audit import write_audit_log
from app.services.storage import (
    StorageValidationError,
    file_exists,
    resolve_stored_path,
    save_bytes,
)
from app.templating import DOCUMENT_CATEGORY_LABELS, base_context, templates

router = APIRouter(tags=["documents"])


@router.get("/admin/documents/upload", response_class=HTMLResponse)
async def upload_document_page(
    request: Request,
    admin_id: UUID = Depends(require_admin),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin/upload_document.html",
        context={
            **base_context(),
            "title": "Загрузка документа",
            "categories": DOCUMENT_CATEGORY_LABELS,
            "error": None,
            "success": None,
        },
    )


@router.post("/documents/upload", response_model=None)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: DocumentCategory = Form(...),
    year: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    admin_id: UUID = Depends(require_admin),
):
    title = title.strip()
    if not title:
        return _upload_form_error(request, "Укажите название документа.")

    if not file.filename:
        return _upload_form_error(request, "Выберите файл для загрузки.")

    content = await file.read()
    try:
        stored_filename, mime_type, file_size = save_bytes(
            content,
            category=category.value,
            original_filename=file.filename,
            content_type=file.content_type,
        )
    except StorageValidationError as exc:
        return _upload_form_error(request, str(exc))

    document = Document(
        title=title,
        category=category,
        year=year,
        stored_filename=stored_filename,
        original_filename=file.filename,
        mime_type=mime_type,
        file_size_bytes=file_size,
        uploaded_by_id=admin_id,
    )
    db.add(document)
    await db.flush()
    await write_audit_log(
        db,
        action=AuditAction.document_uploaded,
        request=request,
        admin_user_id=admin_id,
        metadata={
            "document_id": str(document.id),
            "title": title,
            "category": category.value,
            "stored_filename": stored_filename,
            "file_size_bytes": file_size,
        },
    )
    await db.commit()

    return RedirectResponse(
        url="/admin/documents/upload?success=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _upload_form_error(request: Request, error: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin/upload_document.html",
        context={
            **base_context(),
            "title": "Загрузка документа",
            "categories": DOCUMENT_CATEGORY_LABELS,
            "error": error,
            "success": None,
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@router.get("/documents/assembly", response_class=HTMLResponse)
async def assembly_archive(
    request: Request,
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    stmt = (
        select(Document)
        .where(Document.category == DocumentCategory.assembly)
        .order_by(Document.year.desc().nullslast(), Document.created_at.desc())
    )
    if year is not None:
        stmt = stmt.where(Document.year == year)

    documents = (await db.scalars(stmt)).all()

    all_assembly = (
        await db.scalars(
            select(Document)
            .where(Document.category == DocumentCategory.assembly)
            .order_by(Document.year.desc().nullslast())
        )
    ).all()

    years: list[int] = sorted(
        {doc.year for doc in all_assembly if doc.year is not None},
        reverse=True,
    )

    by_year: dict[int | None, list[Document]] = defaultdict(list)
    for doc in documents:
        by_year[doc.year].append(doc)

    return templates.TemplateResponse(
        request=request,
        name="documents/assembly.html",
        context={
            **base_context(),
            "title": "Архив собраний",
            "documents_by_year": dict(sorted(by_year.items(), key=lambda x: (x[0] is None, x[0]), reverse=True)),
            "years": years,
            "active_year": year,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_list(
    request: Request,
    category: DocumentCategory | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    stmt = select(Document).order_by(Document.created_at.desc())
    if category is not None:
        stmt = stmt.where(Document.category == category)
    else:
        stmt = stmt.where(Document.category != DocumentCategory.assembly)

    documents = (await db.scalars(stmt)).all()

    return templates.TemplateResponse(
        request=request,
        name="documents/list.html",
        context={
            **base_context(),
            "title": "Документы",
            "documents": documents,
            "categories": DOCUMENT_CATEGORY_LABELS,
            "active_category": category,
        },
    )


@router.get("/files/{document_id}")
async def download_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not file_exists(document.stored_filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл ещё не загружен на сервер. Обратитесь в правление.",
        )

    file_path = resolve_stored_path(document.stored_filename)

    return FileResponse(
        path=file_path,
        media_type=document.mime_type,
        filename=document.original_filename,
    )
