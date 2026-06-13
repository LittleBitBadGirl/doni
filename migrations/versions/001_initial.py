"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

document_category = postgresql.ENUM(
    "charter",
    "protocol",
    "finance",
    "regulation",
    "assembly",
    "other",
    name="document_category",
    create_type=False,
)
audit_action = postgresql.ENUM(
    "admin_login",
    "document_uploaded",
    "news_published",
    "finance_updated",
    "admin_action",
    name="audit_action",
    create_type=False,
)


def upgrade() -> None:
    document_category.create(op.get_bind(), checkfirst=True)
    audit_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "admin_users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "contact_info",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("phones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("map_embed_url", sa.String(length=1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.UUID(), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", document_category, nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("stored_filename", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "finance_info",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("membership_fee_per_sotka", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("target_fee_per_plot", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("payment_deadline", sa.Date(), nullable=True),
        sa.Column("bank_details", sa.Text(), nullable=False),
        sa.Column("debtors_filename", sa.String(length=500), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("updated_by_id", sa.UUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "infrastructure_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_by_id", sa.UUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "news",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("news")
    op.drop_table("infrastructure_pages")
    op.drop_table("finance_info")
    op.drop_table("documents")
    op.drop_table("audit_logs")
    op.drop_table("contact_info")
    op.drop_table("admin_users")

    audit_action.drop(op.get_bind(), checkfirst=True)
    document_category.drop(op.get_bind(), checkfirst=True)
