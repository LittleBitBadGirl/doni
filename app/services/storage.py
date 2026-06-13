"""Локальное файловое хранилище: save / delete / resolve path."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.config import Settings, get_settings

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".csv", ".doc", ".docx"})

ALLOWED_MIME_BY_EXT: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf"}),
    ".csv": frozenset({"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}),
    ".doc": frozenset({"application/msword"}),
    ".docx": frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ),
}

DEBTORS_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".csv"})


class StorageValidationError(ValueError):
    pass


def get_upload_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.upload_dir).resolve()


def resolve_stored_path(relative_path: str, settings: Settings | None = None) -> Path:
    """Безопасно разрешает относительный путь внутри upload root."""
    if not relative_path or relative_path.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый путь к файлу",
        )

    upload_root = get_upload_root(settings)
    file_path = (upload_root / relative_path).resolve()

    if file_path != upload_root and upload_root not in file_path.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый путь к файлу",
        )

    return file_path


def public_upload_url(relative_path: str) -> str:
    return f"/uploads/{relative_path.lstrip('/')}"


def _normalize_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if not ext:
        raise StorageValidationError("У файла нет расширения")
    return ext


def _guess_mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def validate_upload(
    *,
    filename: str,
    content_type: str | None,
    size_bytes: int,
    allowed_extensions: frozenset[str] | None = None,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """Проверяет размер, расширение и MIME. Возвращает (extension, mime_type)."""
    settings = settings or get_settings()
    allowed = allowed_extensions or ALLOWED_EXTENSIONS

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes <= 0:
        raise StorageValidationError("Файл пустой")
    if size_bytes > max_bytes:
        raise StorageValidationError(
            f"Файл слишком большой. Максимум {settings.max_upload_size_mb} МБ."
        )

    ext = _normalize_extension(filename)
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise StorageValidationError(f"Недопустимый тип файла. Разрешены: {allowed_list}")

    declared_mime = (content_type or "").split(";", 1)[0].strip().lower()
    expected_mimes = ALLOWED_MIME_BY_EXT.get(ext, frozenset())
    guessed_mime = _guess_mime_type(filename)

    if declared_mime and declared_mime not in expected_mimes:
        if declared_mime != guessed_mime or guessed_mime not in expected_mimes:
            raise StorageValidationError(
                f"Тип содержимого «{declared_mime}» не соответствует расширению {ext}"
            )

    mime_type = declared_mime if declared_mime in expected_mimes else guessed_mime
    if mime_type not in expected_mimes:
        mime_type = next(iter(expected_mimes))

    return ext, mime_type


def save_bytes(
    content: bytes,
    *,
    category: str,
    original_filename: str,
    content_type: str | None = None,
    allowed_extensions: frozenset[str] | None = None,
    settings: Settings | None = None,
) -> tuple[str, str, int]:
    """
    Сохраняет файл в data/uploads/{category}/{uuid}.{ext}.
    Возвращает (stored_filename, mime_type, file_size_bytes).
    """
    settings = settings or get_settings()
    ext, mime_type = validate_upload(
        filename=original_filename,
        content_type=content_type,
        size_bytes=len(content),
        allowed_extensions=allowed_extensions,
        settings=settings,
    )

    file_id = uuid.uuid4()
    stored_filename = f"{category.strip('/')}/{file_id}{ext}"
    file_path = resolve_stored_path(stored_filename, settings)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)

    return stored_filename, mime_type, len(content)


def delete_stored_file(relative_path: str | None, settings: Settings | None = None) -> bool:
    """Удаляет файл с диска. Возвращает True, если файл был удалён."""
    if not relative_path:
        return False

    file_path = resolve_stored_path(relative_path, settings)
    if not file_path.is_file():
        return False

    file_path.unlink()
    return True


def file_exists(relative_path: str, settings: Settings | None = None) -> bool:
    file_path = resolve_stored_path(relative_path, settings)
    return file_path.is_file()
