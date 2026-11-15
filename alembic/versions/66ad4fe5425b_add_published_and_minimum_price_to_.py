"""add_published_and_minimum_price_to_commerce_product

Revision ID: 66ad4fe5425b
Revises: b712823239b1
Create Date: 2026-11-14 16:15:34.051029

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "66ad4fe5425b"
down_revision: str | Sequence[str] | None = "b712823239b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "commerce_product",
        sa.Column(
            "published_price",
            sa.Float(),
            nullable=True,
            comment="Precio de venta específico para este lote físico",
        ),
    )
    op.add_column(
        "commerce_product",
        sa.Column(
            "minimum_price",
            sa.Float(),
            nullable=True,
            comment="Piso mínimo de regateo específico para este lote físico",
        ),
    )
    # Prellenar productos existentes heredando de su Ficha Maestra
    op.execute(
        """
        UPDATE commerce_product
        SET
            published_price = commerce_product_master.published_price,
            minimum_price = commerce_product_master.minimum_price
        FROM commerce_product_master
        WHERE commerce_product.master_product_id = commerce_product_master.id
          AND (
              commerce_product.published_price IS NULL
              OR commerce_product.minimum_price IS NULL
          );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("commerce_product", "minimum_price")
    op.drop_column("commerce_product", "published_price")
