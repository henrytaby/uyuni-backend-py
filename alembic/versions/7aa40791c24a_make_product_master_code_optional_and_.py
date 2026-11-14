"""make_product_master_code_optional_and_add_sequence

Revision ID: 7aa40791c24a
Revises: e976c6814a87
Create Date: 2026-11-13 14:27:56.937427

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7aa40791c24a"
down_revision: str | Sequence[str] | None = "e976c6814a87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make code nullable, drop unique constraint, and add atomic sequence."""
    # 1. Hacer 'code' nullable
    op.alter_column(
        "commerce_product_master",
        "code",
        existing_type=sa.String(length=50),
        nullable=True,
    )

    # 2. Reemplazar índice UNIQUE por índice normal (preparando multi-tenancy)
    op.drop_index(
        "ix_commerce_product_master_code", table_name="commerce_product_master"
    )
    op.create_index(
        "ix_commerce_product_master_code",
        "commerce_product_master",
        ["code"],
        unique=False,
    )

    # 3. Limpiar valores antiguos de 'code' (poner NULL para evitar confusiones)
    op.execute("UPDATE commerce_product_master SET code = NULL;")

    # 4. Crear y asociar la secuencia atómica para item_number (PostgreSQL)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE SEQUENCE IF NOT EXISTS commerce_product_master_item_number_seq;
            SELECT setval(
                'commerce_product_master_item_number_seq',
                GREATEST(COALESCE((SELECT MAX(item_number) FROM commerce_product_master), 1), 1),
                (SELECT MAX(item_number) FROM commerce_product_master) IS NOT NULL
            );
            ALTER TABLE commerce_product_master
            ALTER COLUMN item_number
            SET DEFAULT nextval('commerce_product_master_item_number_seq');
        """)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            ALTER TABLE commerce_product_master ALTER COLUMN item_number DROP DEFAULT;
            DROP SEQUENCE IF EXISTS commerce_product_master_item_number_seq;
        """)

    op.drop_index(
        "ix_commerce_product_master_code", table_name="commerce_product_master"
    )
    op.create_index(
        "ix_commerce_product_master_code",
        "commerce_product_master",
        ["code"],
        unique=True,
    )

    # Restaurar código si es necesario
    op.execute(
        "UPDATE commerce_product_master "
        "SET code = item_number::text WHERE code IS NULL;"
    )

    op.alter_column(
        "commerce_product_master",
        "code",
        existing_type=sa.String(length=50),
        nullable=False,
    )
