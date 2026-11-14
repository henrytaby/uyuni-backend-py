"""add_costing_method_to_commerce_batch

Revision ID: b712823239b1
Revises: a91497080946
Create Date: 2026-11-14 09:58:05.031373

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b712823239b1"
down_revision: str | Sequence[str] | None = "a91497080946"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "commerce_batch",
        sa.Column(
            "costing_method",
            sa.String(length=50),
            nullable=False,
            server_default="WEIGHTED_RETAIL",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("commerce_batch", "costing_method")
