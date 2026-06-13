from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://tsndoni:tsndoni@localhost:5432/tsndoni"

    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 20

    mail_server: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@tsndoni.ru"

    yandex_metrica_id: str = ""

    public_site_url: str = "http://localhost:8080"

    # Bot 1: сайт/админка → чат СНТ (исходящий автопост)
    telegram_publish_enabled: bool = False
    telegram_publish_bot_token: str = ""
    telegram_publish_chat_id: str = ""

    # Публичная ссылка на чат/канал СНТ (кнопка на сайте)
    telegram_subscribe_url: str = ""

    # Bot 2: Telegram → сайт (входящий, раздел «Важно!»)
    telegram_inlet_enabled: bool = False
    telegram_inlet_bot_token: str = ""
    telegram_inlet_webhook_secret: str = ""
    telegram_inlet_allowed_user_ids: str = ""
    telegram_inlet_bot_url: str = ""
    telegram_inlet_use_polling: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_inlet_allowed_user_ids(self) -> set[int]:
        raw = self.telegram_inlet_allowed_user_ids.strip()
        if not raw:
            return set()
        return {int(item.strip()) for item in raw.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
