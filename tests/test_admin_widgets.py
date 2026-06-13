import json

from wtforms import Form

from app.admin_widgets import WYSIWYG_CSS_CLASS, HtmlEditorField, PhonesEditorField, _normalize_phones
from app.html_text import rich_text


class _SampleForm(Form):
    content = HtmlEditorField()


class _PhonesForm(Form):
    phones = PhonesEditorField()


def test_html_editor_field_renders_wysiwyg_class():
    form = _SampleForm(content="<p>Тест</p>")
    html = str(form.content())

    assert WYSIWYG_CSS_CLASS in html
    assert "Тест" in html


def test_normalize_phones_filters_empty_rows():
    phones = _normalize_phones(
        [
            {"label": "Правление", "number": "+7 812"},
            {"label": "", "number": ""},
            "invalid",
        ]
    )

    assert phones == [{"label": "Правление", "number": "+7 812"}]


def test_phones_editor_field_parses_json():
    payload = json.dumps(
        [{"label": "Аварийная", "number": "+7 812 111"}],
        ensure_ascii=False,
    )
    form = _PhonesForm()
    form.phones.process_formdata([payload])

    assert form.phones.data == [{"label": "Аварийная", "number": "+7 812 111"}]


def test_rich_text_renders_plain_text_with_line_breaks():
    result = rich_text("Строка 1\nСтрока 2")

    assert "Строка 1<br>Строка 2" in str(result)
    assert "<p>" not in str(result)


def test_rich_text_keeps_existing_html():
    result = rich_text("<p>Уже <strong>HTML</strong></p>")

    assert str(result) == "<p>Уже <strong>HTML</strong></p>"
