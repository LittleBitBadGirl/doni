#!/usr/bin/env python3
"""Render public templates with mock data for offline UI preview."""

import re
from typing import Optional
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader, select_autoescape

CATEGORY_LABELS = {
    "charter": "Устав",
    "protocol": "Протоколы",
    "finance": "Финансы",
    "regulation": "Регламенты",
    "assembly": "Архив собраний",
    "other": "Прочее",
}

_TAG_RE = re.compile(r"<[^>]+>")


def category_label(category) -> str:
    value = getattr(category, "value", category)
    return CATEGORY_LABELS.get(str(value), str(value))


def format_datetime(value, fmt: str = "%d.%m.%Y") -> str:
    if value is None:
        return ""
    return value.strftime(fmt)


def format_datetime_long(value) -> str:
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


def format_money(value) -> str:
    if value is None:
        return ""
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    int_part = int(amount)
    formatted = f"{int_part:,}".replace(",", "\u00a0")
    if amount == amount.to_integral_value():
        return f"{formatted}\u00a0₽"
    fractional = str(amount).split(".")[1].rstrip("0")
    return f"{formatted},{fractional}\u00a0₽"


def format_date(value) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y")


def phone_tel(value: str) -> str:
    return re.sub(r"[^\d+]", "", value)

TEMPLATES_DIR = ROOT / "app" / "templates"
PREVIEW_DIR = ROOT / "preview"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)

from enum import Enum


class MockDocumentCategory(Enum):
    charter = "charter"
    protocol = "protocol"
    finance = "finance"
    regulation = "regulation"
    assembly = "assembly"
    other = "other"


DOCUMENT_CATEGORIES = {
    MockDocumentCategory.charter: "Устав",
    MockDocumentCategory.protocol: "Протоколы",
    MockDocumentCategory.finance: "Финансы",
    MockDocumentCategory.regulation: "Регламенты",
    MockDocumentCategory.assembly: "Архив собраний",
    MockDocumentCategory.other: "Прочее",
}

CHECKS = [
    ("Fraunces font", r"Fraunces"),
    ("Newsreader font", r"Newsreader"),
    ("No Inter font", r"Inter"),
    ("site-header", r"site-header"),
    ("page-title", r"page-title"),
    ("output.css", r"/static/css/output\.css"),
]


def fake_url_for(name: str, **kwargs: str) -> str:
    if name == "static":
        return f"/static/{kwargs.get('path', '')}"
    if name == "admin_login_submit":
        return "/admin/login"
    return "#"


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters.update(
        {
            "category_label": category_label,
            "format_datetime": format_datetime,
            "format_datetime_long": format_datetime_long,
            "format_date": format_date,
            "format_money": format_money,
            "excerpt": excerpt,
            "format_file_size": format_file_size,
            "phone_tel": phone_tel,
        }
    )
    env.globals["url_for"] = fake_url_for
    return env


def news_item(
    item_id: int,
    title: str,
    content: str,
    *,
    pinned: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        title=title,
        content=content,
        is_pinned=pinned,
        published_at=NOW,
    )


def document_item(
    item_id: int,
    title: str,
    category: str,
    *,
    year: Optional[int] = None,
    size: int = 204800,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        title=title,
        category=category,
        year=year,
        file_size_bytes=size,
    )


def base_context() -> dict:
    return {"yandex_metrica_id": None, "title": "ТСН «ДОНИ»"}


PAGES: list[tuple[str, str, dict]] = [
    (
        "index.html",
        "index.html",
        {
            **base_context(),
            "title": "Главная",
            "pinned_news": [
                news_item(
                    1,
                    "Субботник 15 марта",
                    "<p>Просим всех собственников принять участие в весеннем субботнике.</p>",
                    pinned=True,
                )
            ],
            "recent_news": [
                news_item(2, "График просушки дорог", "<p>Дороги будут закрыты с 10 по 20 марта.</p>"),
                news_item(3, "Оплата взносов до 1 апреля", "<p>Напоминаем о сроках оплаты целевых взносов.</p>"),
            ],
        },
    ),
    (
        "news/list.html",
        "news/index.html",
        {
            **base_context(),
            "title": "Новости",
            "news_items": [
                news_item(1, "Субботник 15 марта", "<p>Текст объявления.</p>", pinned=True),
                news_item(2, "График просушки дорог", "<p>Текст объявления.</p>"),
            ],
            "page": 1,
            "total_pages": 2,
        },
    ),
    (
        "news/detail.html",
        "news/1.html",
        {
            **base_context(),
            "news_item": news_item(
                1,
                "Субботник 15 марта",
                "<p>Просим всех собственников принять участие.</p><h2>Что взять с собой</h2><ul><li>Перчатки</li><li>Грабли</li></ul>",
                pinned=True,
            ),
        },
    ),
    (
        "finance/index.html",
        "finance/index.html",
        {
            **base_context(),
            "title": "Финансы",
            "finance": SimpleNamespace(
                membership_fee_per_sotka=Decimal("1900"),
                target_fee_per_plot=Decimal("8900"),
                payment_deadline=date(2026, 3, 1),
                bank_details="Получатель: ТСН «ДОНИ»\nИНН: 0000000000\nР/с: 40702810...",
                debtors_filename="debtors-2026.pdf",
                updated_at=NOW,
            ),
            "debtors_available": True,
        },
    ),
    (
        "documents/list.html",
        "documents/index.html",
        {
            **base_context(),
            "title": "Документы",
            "active_category": None,
            "categories": DOCUMENT_CATEGORIES,
            "documents": [
                document_item(1, "Устав ТСН «ДОНИ»", "charter", year=2020),
                document_item(2, "Протокол №30", "protocol", year=2025),
            ],
        },
    ),
    (
        "documents/assembly.html",
        "documents/assembly.html",
        {
            **base_context(),
            "title": "Архив собраний",
            "active_year": None,
            "years": [2025, 2024, 2023],
            "documents_by_year": {
                2025: [document_item(3, "Материалы собрания 2025", "assembly", year=2025)],
            },
        },
    ),
    (
        "contacts.html",
        "contacts.html",
        {
            **base_context(),
            "title": "Контакты",
            "contact": SimpleNamespace(
                address="196605, Санкт-Петербург, Пушкинский район, пос. Дони, ул. Примерная, д. 1",
                phones=[
                    SimpleNamespace(label="Председатель", number="+7 (812) 000-00-00"),
                    SimpleNamespace(label="Правление", number="+7 (921) 000-00-00"),
                ],
                map_embed_url=(
                    "https://yandex.ru/map-widget/v1/"
                    "?ll=30.222776%2C59.674360"
                    "&pt=30.222776%2C59.674360%2Cpm2rdm"
                    "&z=16&l=map"
                ),
                updated_at=NOW,
            ),
        },
    ),
    (
        "search/index.html",
        "search/index.html",
        {
            **base_context(),
            "title": "Поиск",
            "query": "взнос",
        },
    ),
    (
        "infrastructure/detail.html",
        "infrastructure/gas.html",
        {
            **base_context(),
            "page": SimpleNamespace(
                title="Газификация",
                slug="gas",
                content="<p>Инструкция по подаче заявки в «Петербурггаз».</p><h2>Необходимые документы</h2><p>Список документов уточняйте в правлении.</p>",
                updated_at=NOW,
            ),
            "active_slug": "gas",
            "nav_pages": [
                SimpleNamespace(slug="gas", title="Газификация"),
                SimpleNamespace(slug="water", title="Водоснабжение"),
                SimpleNamespace(slug="electricity", title="Электроснабжение"),
                SimpleNamespace(slug="landscaping", title="Благоустройство"),
            ],
        },
    ),
    (
        "auth/login.html",
        "admin/login.html",
        {
            **base_context(),
            "title": "Вход",
            "error": None,
            "email": "",
        },
    ),
]


def audit_html(html: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"Inter", html):
        issues.append("found Inter font reference")
    for label, pattern in CHECKS[2:]:
        if label == "No Inter font":
            continue
        if not re.search(pattern, html):
            issues.append(f"missing {label}")
    return issues


def main() -> int:
    env = build_env()
    PREVIEW_DIR.mkdir(exist_ok=True)

    print("Rendering preview pages…")
    failures: list[str] = []

    for template_name, output_name, context in PAGES:
        try:
            template = env.get_template(template_name)
            html = template.render(**context)
            out_path = PREVIEW_DIR / output_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            issues = audit_html(html)
            status = "OK" if not issues else f"WARN: {', '.join(issues)}"
            print(f"  ✓ {output_name:<28} {status}")
            if issues:
                failures.extend(f"{output_name}: {issue}" for issue in issues)
        except Exception as exc:
            print(f"  ✗ {output_name:<28} FAIL: {exc}")
            failures.append(f"{output_name}: render error — {exc}")

    css_path = ROOT / "app" / "static" / "css" / "output.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        for cls in ("site-header", "font-display", "animate-fade-up", "card-hover", "btn-primary"):
            ok = cls in css
            print(f"  {'✓' if ok else '✗'} CSS contains .{cls}")
            if not ok:
                failures.append(f"output.css missing {cls}")
    else:
        failures.append("output.css not found")
        print("  ✗ output.css not found")

    print()
    if failures:
        print("Issues:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("All preview pages rendered successfully.")
    print(f"Preview dir: {PREVIEW_DIR}")
    print("Serve with:")
    print(f"  cd {ROOT} && python3 -m http.server 8765")
    print("Open http://localhost:8765/preview/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
