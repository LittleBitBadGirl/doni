"""Виджеты форм SQLAdmin для не-технических редакторов контента."""

from __future__ import annotations

from wtforms import TextAreaField
from wtforms.widgets import TextArea

WYSIWYG_CSS_CLASS = "wysiwyg-editor"


class HtmlEditorWidget(TextArea):
    """Textarea с классом для инициализации визуального редактора."""

    def __call__(self, field, **kwargs):
        existing = kwargs.get("class", "")
        classes = f"{existing} {WYSIWYG_CSS_CLASS}".strip()
        kwargs["class"] = classes
        kwargs.setdefault("rows", 12)
        return super().__call__(field, **kwargs)


class HtmlEditorField(TextAreaField):
    """Поле HTML-контента: в админке отображается как WYSIWYG, в БД — разметка."""

    widget = HtmlEditorWidget()


HTML_CONTENT_FORM_ARGS = {
    "description": (
        "Выделяйте текст и форматируйте кнопками на панели. "
        "Писать HTML-теги вручную не нужно."
    ),
}
