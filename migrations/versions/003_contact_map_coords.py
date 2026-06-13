"""Update contact map coordinates for TSN DONI

Revision ID: 003
Revises: 002
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTACT_MAP_EMBED_URL = (
    "https://yandex.ru/map-widget/v1/"
    "?ll=30.222776%2C59.674360"
    "&pt=30.222776%2C59.674360%2Cpm2rdm"
    "&z=16&l=map"
)


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE contact_info SET map_embed_url = :url").bindparams(
            url=CONTACT_MAP_EMBED_URL
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE contact_info SET map_embed_url = :url").bindparams(
            url=(
                "https://yandex.ru/map-widget/v1/"
                "?ll=30.404561%2C59.713430&z=14&l=map"
            )
        )
    )
