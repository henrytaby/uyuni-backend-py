"""add_is_public_to_commerce_product_master_image

Revision ID: 9f6eb2dc0e9b
Revises: 66ad4fe5425b
Create Date: 2026-11-14 19:41:05.760258

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f6eb2dc0e9b"
down_revision: str | Sequence[str] | None = "66ad4fe5425b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "commerce_product_master_image",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="¿Visible en catálogo público?",
        ),
    )
    op.create_index(
        op.f("ix_commerce_product_master_image_is_public"),
        "commerce_product_master_image",
        ["is_public"],
        unique=False,
    )
    op.execute(
        """
        UPDATE commerce_product_master_image
        SET is_public = true
        WHERE image_type = 'CATALOG';
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_commerce_product_master_image_is_public"),
        table_name="commerce_product_master_image",
    )
    op.drop_column("commerce_product_master_image", "is_public")
