"""Seed database with development data."""

import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from passlib.context import CryptContext
from sqlalchemy import select

from app.database import async_session_factory
from app.models import (
    AdminUser,
    ContactInfo,
    Document,
    DocumentCategory,
    FinanceInfo,
    InfrastructurePage,
    News,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_EMAIL = "admin@tsndoni.ru"
ADMIN_PASSWORD = "changeme"


async def seed() -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        if existing:
            print("Seed already applied — admin user exists, skipping.")
            return

        admin = AdminUser(
            id=uuid.uuid4(),
            email=ADMIN_EMAIL,
            password_hash=pwd_context.hash(ADMIN_PASSWORD),
            full_name="Администратор правления",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(admin)
        await session.flush()

        now = datetime.now(timezone.utc)
        news_items = [
            News(
                title="Срочно: отключение воды 15 июня",
                content="<p>Уважаемые собственники! 15 июня с 10:00 до 14:00 плановое отключение холодной воды для проведения ремонтных работ.</p>",
                is_pinned=True,
                published_at=now,
                created_by_id=admin.id,
            ),
            News(
                title="График взносов на 2026 год",
                content="<p>Утверждён график целевых и членских взносов на 2026 год. Подробности — в разделе «Финансы».</p>",
                is_pinned=True,
                published_at=now,
                created_by_id=admin.id,
            ),
            News(
                title="Протокол собрания №30 опубликован",
                content="<p>Материалы общего собрания собственников (протокол №30) размещены в разделе «Документы».</p>",
                is_pinned=False,
                published_at=now,
                created_by_id=admin.id,
            ),
            News(
                title="Ход газификации участков",
                content="<p>Правление информирует о текущем статусе подключения газа. Актуальная информация — в разделе «Инфраструктура → Газ».</p>",
                is_pinned=False,
                published_at=now,
                created_by_id=admin.id,
            ),
            News(
                title="Весеннее благоустройство территории",
                content="<p>Запланированы работы по уборке и озеленению общих территорий. Просим собственников не оставлять строительный мусор у въезда.</p>",
                is_pinned=False,
                published_at=now,
                created_by_id=admin.id,
            ),
        ]
        session.add_all(news_items)

        documents = [
            Document(
                title="Устав ТСН «ДОНИ»",
                category=DocumentCategory.charter,
                year=None,
                stored_filename="documents/charter-ustav.pdf",
                original_filename="Устав ТСН ДОНИ.pdf",
                mime_type="application/pdf",
                file_size_bytes=512_000,
                uploaded_by_id=admin.id,
            ),
            Document(
                title="Протокол общего собрания №30",
                category=DocumentCategory.protocol,
                year=2025,
                stored_filename="documents/protocol-30.pdf",
                original_filename="Протокол №30.pdf",
                mime_type="application/pdf",
                file_size_bytes=256_000,
                uploaded_by_id=admin.id,
            ),
            Document(
                title="Материалы собрания 2024",
                category=DocumentCategory.assembly,
                year=2024,
                stored_filename="documents/assembly-2024.pdf",
                original_filename="Собрание 2024.pdf",
                mime_type="application/pdf",
                file_size_bytes=384_000,
                uploaded_by_id=admin.id,
            ),
            Document(
                title="Материалы собрания 2023",
                category=DocumentCategory.assembly,
                year=2023,
                stored_filename="documents/assembly-2023.pdf",
                original_filename="Собрание 2023.pdf",
                mime_type="application/pdf",
                file_size_bytes=320_000,
                uploaded_by_id=admin.id,
            ),
            Document(
                title="Материалы собрания 2025",
                category=DocumentCategory.assembly,
                year=2025,
                stored_filename="documents/assembly-2025.pdf",
                original_filename="Собрание 2025.pdf",
                mime_type="application/pdf",
                file_size_bytes=400_000,
                uploaded_by_id=admin.id,
            ),
            Document(
                title="Положение о членских взносах",
                category=DocumentCategory.regulation,
                year=None,
                stored_filename="documents/regulation-fees.pdf",
                original_filename="Положение о взносах.pdf",
                mime_type="application/pdf",
                file_size_bytes=128_000,
                uploaded_by_id=admin.id,
            ),
        ]
        session.add_all(documents)

        finance = FinanceInfo(
            membership_fee_per_sotka=Decimal("1900.00"),
            target_fee_per_plot=Decimal("8900.00"),
            payment_deadline=date(2026, 3, 1),
            bank_details=(
                "Получатель: ТСН «ДОНИ»\n"
                "ИНН: 0000000000\n"
                "Р/с: 40703810900000000000\n"
                "Банк: ПАО «Пример»\n"
                "БИК: 044030000\n"
                "Назначение: членский/целевой взнос, участок №___"
            ),
            debtors_filename=None,
            is_current=True,
            updated_by_id=admin.id,
        )
        session.add(finance)

        infra_pages = [
            InfrastructurePage(
                slug="gas",
                title="Газификация",
                content="<p>Информация о ходе подключения участков к газоснабжению. Сроки и порядок подачи заявок уточняйте в правлении.</p>",
                updated_by_id=admin.id,
            ),
            InfrastructurePage(
                slug="water",
                title="Водоснабжение",
                content="<p>Сведения о централизованном и индивидуальном водоснабжении, плановых отключениях и аварийных работах.</p>",
                updated_by_id=admin.id,
            ),
            InfrastructurePage(
                slug="electricity",
                title="Электроснабжение",
                content="<p>Контакты энергоснабжающей организации, порядок оформления мощности и типовые вопросы по электросетям.</p>",
                updated_by_id=admin.id,
            ),
            InfrastructurePage(
                slug="landscaping",
                title="Благоустройство",
                content="<p>Планы работ по содержанию дорог, освещению и озеленению общих территорий ТСН «ДОНИ».</p>",
                updated_by_id=admin.id,
            ),
        ]
        session.add_all(infra_pages)

        contact = ContactInfo(
            address="196601, Санкт-Петербург, г. Пушкин, [адрес правления ТСН «ДОНИ»]",
            phones=[
                {"label": "Правление", "number": "+7 (812) 000-00-00"},
                {"label": "Аварийная служба", "number": "+7 (812) 000-00-01"},
            ],
            map_embed_url=(
                "https://yandex.ru/map-widget/v1/?ll=30.404561%2C59.713430&z=14&l=map"
            ),
        )
        session.add(contact)

        await session.commit()
        print("Seed completed successfully.")
        print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
