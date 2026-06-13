"""Виджеты форм SQLAdmin для не-технических редакторов контента."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from markupsafe import Markup, escape
from wtforms import Field, TextAreaField
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


WYSIWYG_FORM_ARGS = {
    "description": (
        "Выделяйте текст и форматируйте кнопками на панели. "
        "Писать HTML-теги вручную не нужно."
    ),
}


class WysiwygAdminMixin:
    """Подключает TinyMCE к указанным полям формы SQLAdmin."""

    wysiwyg_fields: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.wysiwyg_fields:
            return

        overrides = dict(getattr(cls, "form_overrides", None) or {})
        for field_name in cls.wysiwyg_fields:
            overrides[field_name] = HtmlEditorField
        cls.form_overrides = overrides

        args = dict(getattr(cls, "form_args", None) or {})
        for field_name in cls.wysiwyg_fields:
            args.setdefault(field_name, WYSIWYG_FORM_ARGS)
        cls.form_args = args


def _normalize_phones(value: Any) -> list[dict[str, str]]:
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []

    phones: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        number = str(item.get("number", "")).strip()
        if label or number:
            phones.append({"label": label, "number": number})
    return phones


class PhonesEditorWidget:
    """Список телефонов: подпись + номер без JSON."""

    def __call__(self, field, **kwargs):
        phones = _normalize_phones(field.data)
        if not phones:
            phones = [{"label": "", "number": ""}]

        rows = []
        for index, phone in enumerate(phones):
            rows.append(
                f"""
                <div class="phone-row border rounded p-3 mb-3" data-index="{index}">
                  <div class="row g-2 align-items-end">
                    <div class="col-md-5">
                      <label class="form-label">Подпись</label>
                      <input type="text" class="form-control phone-label"
                        data-index="{index}" value="{escape(phone.get('label', ''))}"
                        placeholder="Правление">
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Номер</label>
                      <input type="text" class="form-control phone-number"
                        data-index="{index}" value="{escape(phone.get('number', ''))}"
                        placeholder="+7 (812) 000-00-00">
                    </div>
                    <div class="col-md-1">
                      <button type="button" class="btn btn-outline-danger btn-sm phone-remove"
                        title="Удалить" aria-label="Удалить телефон">×</button>
                    </div>
                  </div>
                </div>
                """
            )

        hidden_value = escape(json.dumps(phones, ensure_ascii=False))
        return Markup(
            f"""
            <div class="phones-editor" data-field-id="{escape(field.id)}">
              <div class="phones-rows">{''.join(rows)}</div>
              <button type="button" class="btn btn-sm btn-outline-secondary phone-add">
                + Добавить телефон
              </button>
              <input type="hidden" name="{escape(field.name)}" id="{escape(field.id)}"
                class="phones-json-input" value="{hidden_value}">
              <div class="form-text text-muted mt-2">
                Укажите подпись (например, «Правление») и номер телефона.
              </div>
            </div>
            """
        )


class PhonesEditorField(Field):
    """JSONB-поле телефонов с понятным интерфейсом для правления."""

    widget = PhonesEditorWidget()

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = []
            return
        raw = valuelist[0]
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Некорректный формат списка телефонов") from exc
        self.data = _normalize_phones(parsed)
