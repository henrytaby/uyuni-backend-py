"""remove_physical_condition_from_commerce_product

Revision ID: 91b73d99d7e1
Revises: f6c115453a45
Create Date: 2026-11-28 12:20:36.927547

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91b73d99d7e1"
down_revision: str | Sequence[str] | None = "f6c115453a45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop physical_condition and its GIN index from commerce_product."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "ix_commerce_product_physical_condition_trgm",
            table_name="commerce_product",
            if_exists=True,
        )

    with op.batch_alter_table("commerce_product") as batch_op:
        batch_op.drop_column("physical_condition")


def downgrade() -> None:
    """Restore physical_condition and its GIN index on commerce_product."""
    with op.batch_alter_table("commerce_product") as batch_op:
        batch_op.add_column(
            sa.Column(
                "physical_condition",
                sa.String(length=50),
                nullable=False,
                server_default="OPERATIONAL",
            )
        )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "UPDATE commerce_product "
            "SET physical_condition = 'DAMAGED_SCRAP' "
            "WHERE status = 'SCRAPPED'"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_commerce_product_physical_condition_trgm "
            "ON commerce_product USING gin "
            "(immutable_unaccent(physical_condition) gin_trgm_ops)"
        )
