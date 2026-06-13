"""Форматтеры колонок SQLAdmin для понятного отображения без IT-терминов."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.models.audit import AuditAction
from app.models.document import DocumentCategory
from app.models.news import NewsSource

MSK = ZoneInfo("Europe/Moscow")

MONTHS_GENITIVE = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

NEWS_SOURCE_LABELS = {
    NewsSource.admin: "Правление",
    NewsSource.telegram_inlet: "Telegram",
}

DOCUMENT_CATEGORY_LABELS = {
    DocumentCategory.charter: "Устав",
    DocumentCategory.protocol: "Протокол",
    DocumentCategory.finance: "Финансы",
    DocumentCategory.regulation: "Регламент",
    DocumentCategory.assembly: "Собрание",
    DocumentCategory.other: "Прочее",
}

AUDIT_ACTION_LABELS = {
    AuditAction.admin_login: "Вход в систему",
    AuditAction.document_uploaded: "Загрузка документа",
    AuditAction.news_published: "Публикация новости",
    AuditAction.finance_updated: "Обновление финансов",
    AuditAction.admin_action: "Действие администратора",
}

INFRA_SLUG_LABELS = {
    "gas": "Газ",
    "water": "Вода",
    "electricity": "Электричество",
    "landscaping": "Благоустройство",
}


def _enum_label(value: Any, labels: dict[Any, str]) -> str:
    if value is None:
        return "—"
    key = value.value if hasattr(value, "value") else value
    return labels.get(value, labels.get(key, str(value)))


def format_datetime_msk(model: Any, attribute: Any) -> str:
    value = getattr(model, attribute.key, None)
    if value is None:
        return "—"
    if isinstance(value, date) and not isinstance(value, datetime):
        return f"{value.day} {MONTHS_GENITIVE[value.month]} {value.year}"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(MSK)
    return (
        f"{local.day} {MONTHS_GENITIVE[local.month]} {local.year} "
        f"{local.strftime('%H:%M')}"
    )


def format_admin_user(model: Any, attribute: Any) -> str:
    user = getattr(model, attribute.key, None)
    if user is None:
        return "—"
    return user.full_name


def format_news_source(model: Any, attribute: Any) -> str:
    return _enum_label(getattr(model, attribute.key, None), NEWS_SOURCE_LABELS)


def format_document_category(model: Any, attribute: Any) -> str:
    return _enum_label(getattr(model, attribute.key, None), DOCUMENT_CATEGORY_LABELS)


def format_audit_action(model: Any, attribute: Any) -> str:
    return _enum_label(getattr(model, attribute.key, None), AUDIT_ACTION_LABELS)


def format_infra_slug(model: Any, attribute: Any) -> str:
    slug = getattr(model, attribute.key, None)
    if not slug:
        return "—"
    return INFRA_SLUG_LABELS.get(slug, slug)


def format_file_size(model: Any, attribute: Any) -> str:
    size = getattr(model, attribute.key, None)
    if size is None:
        return "—"
    if size < 1024:
        return f"{size} Б"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} КБ"
    return f"{size / (1024 * 1024):.1f} МБ"


def format_rubles(model: Any, attribute: Any) -> str:
    value = getattr(model, attribute.key, None)
    if value is None:
        return "—"
    amount = Decimal(value)
    whole, fraction = f"{amount:.2f}".split(".")
    whole_spaced = f"{int(whole):,}".replace(",", " ")
    return f"{whole_spaced},{fraction} ₽"
