"""rename_to_product_master_external_link_add_is_public_and_drop_external_info_url

Revision ID: b3ff00d4f9b4
Revises: d93fce7fce21
Create Date: 2026-11-13 18:53:55.065160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3ff00d4f9b4'
down_revision: Union[str, Sequence[str], None] = 'd93fce7fce21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Renombrar la tabla a commerce_product_master_external_link
    op.rename_table(
        "commerce_product_external_link",
        "commerce_product_master_external_link",
    )

    # 2. Renombrar los índices para mantener la nomenclatura semántica exacta
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_external_link_id "
        "RENAME TO ix_commerce_product_master_external_link_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_external_link_product_master_id "
        "RENAME TO ix_commerce_product_master_external_link_product_master_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_external_link_portal "
        "RENAME TO ix_commerce_product_master_external_link_portal"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_external_link_is_primary "
        "RENAME TO ix_commerce_product_master_external_link_is_primary"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_external_link_sort_order "
        "RENAME TO ix_commerce_product_master_external_link_sort_order"
    )

    # 3. Agregar la columna is_public (default true) e indexarla
    op.add_column(
        "commerce_product_master_external_link",
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_commerce_product_master_external_link_is_public",
        "commerce_product_master_external_link",
        ["is_public"],
        unique=False,
    )

    # 4. Eliminar el campo redundante external_info_url de commerce_product_master
    op.drop_column("commerce_product_master", "external_info_url")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Recrear el campo external_info_url en commerce_product_master
    op.add_column(
        "commerce_product_master",
        sa.Column("external_info_url", sa.String(length=500), nullable=True),
    )

    # 2. Eliminar índice y columna is_public
    op.drop_index(
        "ix_commerce_product_master_external_link_is_public",
        table_name="commerce_product_master_external_link",
    )
    op.drop_column("commerce_product_master_external_link", "is_public")

    # 3. Revertir nombres de índices
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_external_link_id "
        "RENAME TO ix_commerce_product_external_link_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_external_link_product_master_id "
        "RENAME TO ix_commerce_product_external_link_product_master_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_external_link_portal "
        "RENAME TO ix_commerce_product_external_link_portal"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_external_link_is_primary "
        "RENAME TO ix_commerce_product_external_link_is_primary"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_external_link_sort_order "
        "RENAME TO ix_commerce_product_external_link_sort_order"
    )

    # 4. Renombrar la tabla de vuelta
    op.rename_table(
        "commerce_product_master_external_link",
        "commerce_product_external_link",
    )
