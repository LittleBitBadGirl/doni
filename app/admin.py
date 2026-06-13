import logging
from pathlib import Path
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import object_session
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from wtforms import BooleanField, PasswordField
from wtforms.validators import Length, Optional

from app.auth.constants import ADMIN_COOKIE_NAME
from app.auth.jwt import decode_access_token
from app.auth.password import hash_password
from app.config import get_settings
from app.database import async_session_factory, engine
from app.services.storage import delete_stored_file
from app.services.telegram_publish import get_telegram_publish_bot
from app.models import (
    AdminUser,
    AuditLog,
    ContactInfo,
    Document,
    FinanceInfo,
    InfrastructurePage,
    News,
    NewsSource,
)

settings = get_settings()
ADMIN_TEMPLATES_DIR = str(Path(__file__).resolve().parent / "admin_templates")
logger = logging.getLogger(__name__)


class AdminAuthBackend(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        return False

    async def logout(self, request: Request) -> bool:
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.cookies.get(ADMIN_COOKIE_NAME)
        if not token:
            return False
        payload = decode_access_token(token)
        return payload is not None


class AdminUserAdmin(ModelView, model=AdminUser):
    name = "Администратор"
    name_plural = "Администраторы"
    icon = "fa-solid fa-user-shield"
    column_list = [AdminUser.email, AdminUser.full_name, AdminUser.is_active, AdminUser.created_at]
    column_searchable_list = [AdminUser.email, AdminUser.full_name]
    form_columns = [AdminUser.email, AdminUser.full_name, AdminUser.is_active]
    can_create = True
    can_edit = True
    can_delete = False

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.password = PasswordField(
            "Пароль",
            validators=[
                Optional(),
                Length(min=8, message="Минимум 8 символов"),
            ],
        )
        return form_class

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: AdminUser,
        is_created: bool,
        request: Request,
    ) -> None:
        password = str(data.pop("password", "") or "").strip()
        if is_created:
            if not password:
                raise ValueError("Укажите пароль для нового администратора")
            model.password_hash = hash_password(password)
        elif password:
            model.password_hash = hash_password(password)


class NewsAdmin(ModelView, model=News):
    name = "Новость"
    name_plural = "Новости"
    icon = "fa-solid fa-newspaper"
    column_list = [News.title, News.is_pinned, News.source, News.published_at, News.created_by]
    column_searchable_list = [News.title]
    column_sortable_list = [News.published_at, News.is_pinned]
    form_columns = [News.title, News.content, News.is_pinned, News.published_at, News.created_by]
    form_widget_args = {"content": {"rows": 10}}

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.notify_telegram = BooleanField(
            "Отправить в чат СНТ (publish-бот)",
            default=False,
            description=(
                "Publish-бот рассылает только новости из админки. "
                "При создании закреплённой новости отправка выполняется автоматически. "
                "Новости, пришедшие через inlet-бот, сюда не дублируются."
            ),
        )
        return form_class

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: News,
        is_created: bool,
        request: Request,
    ) -> None:
        notify_telegram = bool(data.pop("notify_telegram", False))
        if is_created:
            model.source = NewsSource.admin
        auto_publish = is_created and model.is_pinned and model.source == NewsSource.admin
        request.state.notify_telegram = notify_telegram or auto_publish

    async def after_model_change(
        self,
        data: dict[str, Any],
        model: News,
        is_created: bool,
        request: Request,
    ) -> None:
        if not model.is_pinned:
            return
        if not getattr(request.state, "notify_telegram", False):
            return

        notifier = get_telegram_publish_bot()
        if not notifier.is_enabled:
            return

        result = await notifier.send_important_news(
            news_id=model.id,
            title=model.title,
            content_html=model.content,
        )
        if not result.sent and not result.skipped:
            logger.warning(
                "Не удалось отправить новость %s в Telegram: %s",
                model.id,
                result.error,
            )


class DocumentAdmin(ModelView, model=Document):
    name = "Документ"
    name_plural = "Документы"
    icon = "fa-solid fa-file-pdf"
    column_list = [
        Document.title,
        Document.category,
        Document.year,
        Document.original_filename,
        Document.file_size_bytes,
        Document.created_at,
    ]
    column_searchable_list = [Document.title, Document.original_filename]
    column_sortable_list = [Document.created_at, Document.category, Document.year]
    form_columns = [
        Document.title,
        Document.category,
        Document.year,
    ]
    can_create = False

    async def on_model_delete(self, model: Document, request: Request) -> None:
        delete_stored_file(model.stored_filename)


class FinanceInfoAdmin(ModelView, model=FinanceInfo):
    name = "Финансы"
    name_plural = "Финансы"
    icon = "fa-solid fa-ruble-sign"
    column_list = [
        FinanceInfo.is_current,
        FinanceInfo.membership_fee_per_sotka,
        FinanceInfo.target_fee_per_plot,
        FinanceInfo.payment_deadline,
        FinanceInfo.updated_at,
    ]
    column_details_list = [
        FinanceInfo.membership_fee_per_sotka,
        FinanceInfo.target_fee_per_plot,
        FinanceInfo.payment_deadline,
        FinanceInfo.bank_details,
        FinanceInfo.debtors_filename,
        FinanceInfo.is_current,
        FinanceInfo.updated_at,
    ]
    form_columns = [
        FinanceInfo.membership_fee_per_sotka,
        FinanceInfo.target_fee_per_plot,
        FinanceInfo.payment_deadline,
        FinanceInfo.bank_details,
        FinanceInfo.is_current,
        FinanceInfo.updated_by,
    ]
    form_widget_args = {"bank_details": {"rows": 8}}

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: FinanceInfo,
        is_created: bool,
        request: Request,
    ) -> None:
        if not model.is_current:
            return

        session = object_session(model)
        if session is None:
            return

        await session.execute(
            update(FinanceInfo)
            .where(FinanceInfo.id != model.id, FinanceInfo.is_current.is_(True))
            .values(is_current=False)
        )

    async def on_model_delete(self, model: FinanceInfo, request: Request) -> None:
        delete_stored_file(model.debtors_filename)


class InfrastructurePageAdmin(ModelView, model=InfrastructurePage):
    name = "Инфраструктура"
    name_plural = "Инфраструктура"
    icon = "fa-solid fa-road"
    column_list = [InfrastructurePage.slug, InfrastructurePage.title, InfrastructurePage.updated_at]
    column_searchable_list = [InfrastructurePage.slug, InfrastructurePage.title]
    form_columns = [InfrastructurePage.slug, InfrastructurePage.title, InfrastructurePage.content, InfrastructurePage.updated_by]
    form_widget_args = {"content": {"rows": 10}}


class ContactInfoAdmin(ModelView, model=ContactInfo):
    name = "Контакты"
    name_plural = "Контакты"
    icon = "fa-solid fa-address-book"
    column_list = [ContactInfo.address, ContactInfo.updated_at]
    form_columns = [ContactInfo.address, ContactInfo.phones, ContactInfo.map_embed_url]


class AuditLogAdmin(ModelView, model=AuditLog):
    name = "Аудит"
    name_plural = "Журнал аудита"
    icon = "fa-solid fa-clipboard-list"
    column_list = [
        AuditLog.created_at,
        AuditLog.action,
        AuditLog.admin_user,
        AuditLog.ip_address,
    ]
    column_sortable_list = [AuditLog.created_at, AuditLog.action]
    can_create = False
    can_edit = False
    can_delete = False


def setup_admin(app) -> Admin:
    authentication_backend = AdminAuthBackend(secret_key=settings.secret_key)

    admin = Admin(
        app,
        engine,
        session_maker=async_session_factory,
        authentication_backend=authentication_backend,
        title="ТСН «ДОНИ» — Админ",
        base_url="/admin",
        templates_dir=ADMIN_TEMPLATES_DIR,
    )

    admin.add_view(NewsAdmin)
    admin.add_view(DocumentAdmin)
    admin.add_view(FinanceInfoAdmin)
    admin.add_view(InfrastructurePageAdmin)
    admin.add_view(ContactInfoAdmin)
    admin.add_view(AdminUserAdmin)
    admin.add_view(AuditLogAdmin)

    return admin
