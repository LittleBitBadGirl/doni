"""Unit tests for application settings."""

from app.config import Settings


class TestInletAllowedUserIds:
    def test_should_parse_comma_separated_ids(self):
        settings = Settings(telegram_inlet_allowed_user_ids="123, 456 ,789")

        assert settings.parsed_inlet_allowed_user_ids == {123, 456, 789}

    def test_should_return_empty_set_when_unset(self):
        settings = Settings(telegram_inlet_allowed_user_ids="")

        assert settings.parsed_inlet_allowed_user_ids == set()
