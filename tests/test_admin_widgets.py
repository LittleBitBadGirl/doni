from wtforms import Form

from app.admin_widgets import WYSIWYG_CSS_CLASS, HtmlEditorField


class _SampleForm(Form):
    content = HtmlEditorField()


def test_html_editor_field_renders_wysiwyg_class():
    form = _SampleForm(content="<p>Тест</p>")
    html = str(form.content())

    assert WYSIWYG_CSS_CLASS in html
    assert "Тест" in html
