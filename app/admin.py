import logging
import time
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy import update
from sqlalchemy.orm import object_session
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from wtforms import BooleanField, PasswordField
from wtforms.validators import Length, Optional

from app.admin_export import build_xlsx_response
from app.admin_formatters import (
    format_admin_user,
    format_audit_action,
    format_datetime_msk,
    format_document_category,
    format_file_size,
    format_infra_slug,
    format_news_source,
    format_rubles,
)
from app.auth.constants import ADMIN_COOKIE_NAME
from app.auth.cookies import get_admin_id_from_request
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

DATETIME_FMT = {  # noqa: E501 — общие форматтеры дат для списков и карточек
    "created_at": format_datetime_msk,
    "updated_at": format_datetime_msk,
    "published_at": format_datetime_msk,
    "payment_deadline": format_datetime_msk,
}


def _current_admin_id(request: Request):
    admin_id = get_admin_id_from_request(request)
    if admin_id is None:
        raise ValueError("Сессия администратора истекла. Войдите снова.")
    return admin_id


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


class DoniModelView(ModelView):
    """Базовое представление: без выгрузки (контент редактируется на сайте, не в файлах)."""

    can_export = False
    export_types: ClassVar[list[str]] = ["xlsx"]
    page_size_options = [10, 25, 50]

    def get_export_name(self, export_type: str) -> str:
        label = self.name_plural or self.name
        return f"{label}_{time.strftime('%Y-%m-%d')}.xlsx"

    async def export_data(self, data: list[Any], export_type: str = "xlsx") -> Any:
        if export_type != "xlsx":
            raise NotImplementedError("Поддерживается только выгрузка в Excel (.xlsx)")
        stem = self.get_export_name(export_type).removesuffix(".xlsx")
        return await build_xlsx_response(self, data, stem)


class AdminUserAdmin(DoniModelView, model=AdminUser):
    name = "Администратор"
    name_plural = "Администраторы"
    icon = "fa-solid fa-user-shield"
    column_list = [AdminUser.full_name, AdminUser.email, AdminUser.is_active, AdminUser.created_at]
    column_searchable_list = [AdminUser.email, AdminUser.full_name]
    column_sortable_list = [AdminUser.created_at, AdminUser.full_name]
    column_labels = {
        AdminUser.email: "Эл. почта",
        AdminUser.full_name: "ФИО",
        AdminUser.is_active: "Активен",
        AdminUser.created_at: "Добавлен",
        AdminUser.password_hash: "Пароль (хэш)",
    }
    column_formatters = DATETIME_FMT
    column_formatters_detail = DATETIME_FMT
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


class NewsAdmin(DoniModelView, model=News):
    name = "Новость"
    name_plural = "Новости"
    icon = "fa-solid fa-newspaper"
    column_list = [News.title, News.is_pinned, News.source, News.published_at]
    column_searchable_list = [News.title]
    column_sortable_list = [News.published_at, News.is_pinned]
    column_default_sort = [(News.published_at, True)]
    column_labels = {
        News.title: "Заголовок",
        News.content: "Текст",
        News.is_pinned: "На главной",
        News.source: "Источник",
        News.published_at: "Дата публикации",
        News.created_by: "Автор",
    }
    column_formatters = {
        News.published_at: format_datetime_msk,
        News.source: format_news_source,
        News.created_by: format_admin_user,
    }
    column_formatters_detail = {
        News.published_at: format_datetime_msk,
        News.source: format_news_source,
        News.created_by: format_admin_user,
    }
    form_columns = [News.title, News.content, News.is_pinned, News.published_at]
    form_widget_args = {"content": {"rows": 10}}

    async def scaffold_form(self):
        form_class = await super().scaffold_form()
        form_class.notify_telegram = BooleanField(
            "Отправить в чат СНТ",
            default=False,
            description=(
                "Publish-бот рассылает только новости из админки. "
                "Для закреплённых новостей отправка выполняется автоматически."
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
            model.created_by_id = _current_admin_id(request)
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


class DocumentAdmin(DoniModelView, model=Document):
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
    column_default_sort = [(Document.created_at, True)]
    column_labels = {
        Document.title: "Название",
        Document.category: "Категория",
        Document.year: "Год",
        Document.original_filename: "Имя файла",
        Document.file_size_bytes: "Размер",
        Document.created_at: "Загружен",
        Document.stored_filename: "Путь на сервере",
        Document.mime_type: "Тип файла",
        Document.uploaded_by: "Загрузил",
    }
    column_formatters = {
        Document.category: format_document_category,
        Document.file_size_bytes: format_file_size,
        Document.created_at: format_datetime_msk,
        Document.uploaded_by: format_admin_user,
    }
    column_formatters_detail = {
        Document.category: format_document_category,
        Document.file_size_bytes: format_file_size,
        Document.created_at: format_datetime_msk,
        Document.uploaded_by: format_admin_user,
    }
    form_columns = [
        Document.title,
        Document.category,
        Document.year,
    ]
    can_create = False

    async def on_model_delete(self, model: Document, request: Request) -> None:
        delete_stored_file(model.stored_filename)


class FinanceInfoAdmin(DoniModelView, model=FinanceInfo):
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
    column_labels = {
        FinanceInfo.is_current: "Актуально",
        FinanceInfo.membership_fee_per_sotka: "Взнос за сотку",
        FinanceInfo.target_fee_per_plot: "Целевой взнос за участок",
        FinanceInfo.payment_deadline: "Срок оплаты",
        FinanceInfo.bank_details: "Реквизиты",
        FinanceInfo.debtors_filename: "Список должников (файл)",
        FinanceInfo.updated_at: "Обновлено",
        FinanceInfo.updated_by: "Кто обновил",
    }
    column_formatters = {
        FinanceInfo.membership_fee_per_sotka: format_rubles,
        FinanceInfo.target_fee_per_plot: format_rubles,
        FinanceInfo.payment_deadline: format_datetime_msk,
        FinanceInfo.updated_at: format_datetime_msk,
        FinanceInfo.updated_by: format_admin_user,
    }
    column_formatters_detail = column_formatters
    form_columns = [
        FinanceInfo.membership_fee_per_sotka,
        FinanceInfo.target_fee_per_plot,
        FinanceInfo.payment_deadline,
        FinanceInfo.bank_details,
        FinanceInfo.is_current,
    ]
    form_widget_args = {"bank_details": {"rows": 8}}

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: FinanceInfo,
        is_created: bool,
        request: Request,
    ) -> None:
        model.updated_by_id = _current_admin_id(request)
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


class InfrastructurePageAdmin(DoniModelView, model=InfrastructurePage):
    name = "Инфраструктура"
    name_plural = "Инфраструктура"
    icon = "fa-solid fa-road"
    column_list = [InfrastructurePage.slug, InfrastructurePage.title, InfrastructurePage.updated_at]
    column_searchable_list = [InfrastructurePage.title]
    column_sortable_list = [InfrastructurePage.updated_at, InfrastructurePage.title]
    column_labels = {
        InfrastructurePage.slug: "Раздел",
        InfrastructurePage.title: "Заголовок",
        InfrastructurePage.content: "Содержание",
        InfrastructurePage.updated_at: "Обновлено",
        InfrastructurePage.updated_by: "Кто обновил",
    }
    column_formatters = {
        InfrastructurePage.slug: format_infra_slug,
        InfrastructurePage.updated_at: format_datetime_msk,
        InfrastructurePage.updated_by: format_admin_user,
    }
    column_formatters_detail = column_formatters
    form_columns = [InfrastructurePage.slug, InfrastructurePage.title, InfrastructurePage.content]
    form_widget_args = {
        "content": {"rows": 10},
        "slug": {"readonly": True},
    }

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: InfrastructurePage,
        is_created: bool,
        request: Request,
    ) -> None:
        model.updated_by_id = _current_admin_id(request)


class ContactInfoAdmin(DoniModelView, model=ContactInfo):
    name = "Контакты"
    name_plural = "Контакты"
    icon = "fa-solid fa-address-book"
    column_list = [ContactInfo.address, ContactInfo.updated_at]
    column_labels = {
        ContactInfo.address: "Адрес",
        ContactInfo.phones: "Телефоны",
        ContactInfo.map_embed_url: "Карта (код вставки)",
        ContactInfo.updated_at: "Обновлено",
    }
    column_formatters = {ContactInfo.updated_at: format_datetime_msk}
    column_formatters_detail = column_formatters
    form_columns = [ContactInfo.address, ContactInfo.phones, ContactInfo.map_embed_url]
    form_widget_args = {
        "phones": {"rows": 4},
        "map_embed_url": {"rows": 3},
    }


class AuditLogAdmin(DoniModelView, model=AuditLog):
    name = "Запись"
    name_plural = "Журнал действий"
    icon = "fa-solid fa-clipboard-list"
    can_export = True
    export_max_rows = 5000
    column_list = [
        AuditLog.created_at,
        AuditLog.action,
        AuditLog.admin_user,
    ]
    column_details_exclude_list = [AuditLog.user_agent, AuditLog.audit_metadata]
    column_sortable_list = [AuditLog.created_at, AuditLog.action]
    column_default_sort = [(AuditLog.created_at, True)]
    column_labels = {
        AuditLog.created_at: "Когда",
        AuditLog.action: "Действие",
        AuditLog.admin_user: "Кто",
        AuditLog.ip_address: "IP-адрес",
        AuditLog.user_agent: "Браузер",
        AuditLog.audit_metadata: "Подробности",
    }
    column_formatters = {
        AuditLog.created_at: format_datetime_msk,
        AuditLog.action: format_audit_action,
        AuditLog.admin_user: format_admin_user,
    }
    column_formatters_detail = column_formatters
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True


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
