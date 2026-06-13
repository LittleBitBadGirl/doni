import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FinanceInfo(Base):
    __tablename__ = "finance_info"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    membership_fee_per_sotka: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    target_fee_per_plot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_details: Mapped[str] = mapped_column(Text, nullable=False)
    debtors_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_by: Mapped["AdminUser"] = relationship("AdminUser", lazy="selectin")


from app.models.admin_user import AdminUser  # noqa: E402
