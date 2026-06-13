"""Форматирование HTML и plain text для шаблонов."""

from __future__ import annotations

import html
import re

from markupsafe import Markup

_TAG_RE = re.compile(r"<[^>]+>")


def rich_text(value: str | None) -> Markup:
    """HTML как есть; старый plain text — с переносами строк."""
    if not value:
        return Markup("")
    text = str(value).strip()
    if _TAG_RE.search(text):
        return Markup(text)
    lines = [html.escape(line) for line in text.split("\n")]
    return Markup("<br>".join(lines))
