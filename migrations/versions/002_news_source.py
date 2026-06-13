"""Add news.source for telegram inlet tracking

Revision ID: 002
Revises: 001
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

news_source = postgresql.ENUM(
    "admin",
    "telegram_inlet",
    name="news_source",
    create_type=False,
)


def upgrade() -> None:
    news_source.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "news",
        sa.Column(
            "source",
            news_source,
            nullable=False,
            server_default="admin",
        ),
    )
    op.alter_column("news", "source", server_default=None)


def downgrade() -> None:
    op.drop_column("news", "source")
    news_source.drop(op.get_bind(), checkfirst=True)
