"""rename_to_product_master_image

Revision ID: eaeab392e502
Revises: b3ff00d4f9b4
Create Date: 2026-11-13 19:35:49.070902

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'eaeab392e502'
down_revision: Union[str, Sequence[str], None] = 'b3ff00d4f9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("commerce_product_image", "commerce_product_master_image")

    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_id "
        "RENAME TO ix_commerce_product_master_image_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_image_type "
        "RENAME TO ix_commerce_product_master_image_image_type"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_is_cover "
        "RENAME TO ix_commerce_product_master_image_is_cover"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_product_id "
        "RENAME TO ix_commerce_product_master_image_product_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_product_master_id "
        "RENAME TO ix_commerce_product_master_image_product_master_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_public_id "
        "RENAME TO ix_commerce_product_master_image_public_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_image_sort_order "
        "RENAME TO ix_commerce_product_master_image_sort_order"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_id "
        "RENAME TO ix_commerce_product_image_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_image_type "
        "RENAME TO ix_commerce_product_image_image_type"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_is_cover "
        "RENAME TO ix_commerce_product_image_is_cover"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_product_id "
        "RENAME TO ix_commerce_product_image_product_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_product_master_id "
        "RENAME TO ix_commerce_product_image_product_master_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_public_id "
        "RENAME TO ix_commerce_product_image_public_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_image_sort_order "
        "RENAME TO ix_commerce_product_image_sort_order"
    )

    op.rename_table("commerce_product_master_image", "commerce_product_image")
