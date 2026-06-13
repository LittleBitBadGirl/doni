import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.html_text import rich_text
from app.models.document import DocumentCategory

BASE_DIR = Path(__file__).resolve().parent

INFRASTRUCTURE_SLUGS: list[str] = ["gas", "water", "electricity", "landscaping"]

INFRASTRUCTURE_LABELS: dict[str, str] = {
    "gas": "Газификация",
    "water": "Водоснабжение",
    "electricity": "Электроснабжение",
    "landscaping": "Благоустройство",
}

DOCUMENT_CATEGORY_LABELS: dict[DocumentCategory, str] = {
    DocumentCategory.charter: "Устав",
    DocumentCategory.protocol: "Протоколы",
    DocumentCategory.finance: "Финансы",
    DocumentCategory.regulation: "Регламенты",
    DocumentCategory.assembly: "Архив собраний",
    DocumentCategory.other: "Прочее",
}

MOSCOW = ZoneInfo("Europe/Moscow")
_TAG_RE = re.compile(r"<[^>]+>")


def category_label(category: DocumentCategory | str) -> str:
    if isinstance(category, str):
        try:
            category = DocumentCategory(category)
        except ValueError:
            return category
    return DOCUMENT_CATEGORY_LABELS.get(category, str(category))


def format_datetime(value: datetime | None, fmt: str = "%d.%m.%Y") -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(MOSCOW).strftime(fmt)


def format_datetime_long(value: datetime | None) -> str:
    return format_datetime(value, "%d.%m.%Y %H:%M")


def excerpt(html: str, length: int = 200) -> str:
    text = _TAG_RE.sub("", html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rsplit(" ", 1)[0] + "…"


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} КБ"
    return f"{size_bytes / (1024 * 1024):.1f} МБ"


def format_money(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    int_part = int(amount)
    formatted = f"{int_part:,}".replace(",", "\u00a0")
    if amount == amount.to_integral_value():
        return f"{formatted}\u00a0₽"
    fractional = str(amount).split(".")[1].rstrip("0")
    return f"{formatted},{fractional}\u00a0₽"


def format_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y")


def phone_tel(value: str) -> str:
    return re.sub(r"[^\d+]", "", value)


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["category_label"] = category_label
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_datetime_long"] = format_datetime_long
templates.env.filters["format_date"] = format_date
templates.env.filters["format_money"] = format_money
templates.env.filters["excerpt"] = excerpt
templates.env.filters["rich_text"] = rich_text
templates.env.filters["format_file_size"] = format_file_size
templates.env.filters["phone_tel"] = phone_tel


def base_context() -> dict:
    settings = get_settings()
    return {
        "yandex_metrica_id": settings.yandex_metrica_id,
        "telegram_subscribe_url": settings.telegram_subscribe_url.strip(),
        "telegram_inlet_bot_url": settings.telegram_inlet_bot_url.strip(),
    }
