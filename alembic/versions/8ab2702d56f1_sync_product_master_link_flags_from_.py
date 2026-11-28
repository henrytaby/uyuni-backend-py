"""sync_product_master_link_flags_from_evidence

Revision ID: 8ab2702d56f1
Revises: af139c077206
Create Date: 2026-11-28 11:18:11.488656

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ab2702d56f1"
down_revision: str | Sequence[str] | None = "af139c077206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Sync is_published_marketplace and has_video from real external links."""
    op.execute(
        """
        UPDATE commerce_product_master
        SET
            is_published_marketplace = EXISTS (
                SELECT 1
                FROM commerce_product_master_external_link l
                WHERE l.product_master_id = commerce_product_master.id
                  AND l.link_type = 'MARKETPLACE'
            ),
            has_video = EXISTS (
                SELECT 1
                FROM commerce_product_master_external_link l
                WHERE l.product_master_id = commerce_product_master.id
                  AND l.link_type = 'VIDEO'
            )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
