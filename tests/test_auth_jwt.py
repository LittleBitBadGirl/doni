"""Unit tests for JWT helpers."""

from uuid import uuid4

from app.auth.jwt import create_access_token, decode_access_token
from app.config import Settings
from tests.conftest import _clear_settings_cache


class TestJwtTokens:
    def test_should_roundtrip_admin_token(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "jwt-test-secret")
        _clear_settings_cache()

        admin_id = uuid4()
        token = create_access_token(admin_id, "admin@tsndoni.ru")
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(admin_id)
        assert payload["email"] == "admin@tsndoni.ru"

    def test_should_reject_tampered_token(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "jwt-test-secret")
        _clear_settings_cache()

        token = create_access_token(uuid4(), "admin@tsndoni.ru")

        assert decode_access_token(token + "x") is None

    def test_should_reject_token_with_wrong_secret(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "secret-one")
        _clear_settings_cache()
        token = create_access_token(uuid4(), "admin@tsndoni.ru")

        monkeypatch.setenv("SECRET_KEY", "secret-two")
        _clear_settings_cache()

        assert decode_access_token(token) is None
