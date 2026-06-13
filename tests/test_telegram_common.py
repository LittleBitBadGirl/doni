"""Unit tests for telegram_common helpers."""

from uuid import UUID

import pytest

from app.config import Settings
from app.services.telegram_common import (
    build_public_news_url,
    excerpt_html,
    parse_title_and_body,
    plain_text_to_html,
)


class TestParseTitleAndBody:
    def test_should_split_first_line_as_title(self):
        title, body = parse_title_and_body("Отключение воды\nУважаемые собственники!")

        assert title == "Отключение воды"
        assert body == "Уважаемые собственники!"

    def test_should_use_title_as_body_for_single_line(self):
        title, body = parse_title_and_body("Только заголовок")

        assert title == "Только заголовок"
        assert body == "Только заголовок"

    def test_should_raise_when_message_is_empty(self):
        with pytest.raises(ValueError, match="empty_message"):
            parse_title_and_body("   \n  ")

    def test_should_truncate_title_to_500_chars(self):
        long_line = "A" * 600
        title, _ = parse_title_and_body(f"{long_line}\nbody")

        assert len(title) == 500


class TestPlainTextToHtml:
    def test_should_wrap_paragraphs(self):
        html = plain_text_to_html("Line one\n\nLine two")

        assert html == "<p>Line one</p><p>Line two</p>"

    def test_should_escape_html_characters(self):
        html = plain_text_to_html("<script>alert(1)</script>")

        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_should_return_empty_paragraph_for_blank_input(self):
        assert plain_text_to_html("   ") == "<p></p>"


class TestExcerptHtml:
    def test_should_strip_tags_and_shorten(self):
        html = "<p>" + "word " * 100 + "</p>"
        excerpt = excerpt_html(html, length=50)

        assert "<" not in excerpt
        assert len(excerpt) <= 50

    def test_should_return_full_text_when_short(self):
        assert excerpt_html("<p>Короткий текст</p>") == "Короткий текст"


class TestBuildPublicNewsUrl:
    def test_should_build_absolute_url(self):
        settings = Settings(public_site_url="https://tsndoni.ru")
        news_id = UUID("00000000-0000-0000-0000-000000000001")

        url = build_public_news_url(settings, news_id)

        assert url == "https://tsndoni.ru/news/00000000-0000-0000-0000-000000000001"

    def test_should_return_path_when_base_url_empty(self):
        settings = Settings(public_site_url="")
        news_id = UUID("00000000-0000-0000-0000-000000000002")

        assert build_public_news_url(settings, news_id) == f"/news/{news_id}"
