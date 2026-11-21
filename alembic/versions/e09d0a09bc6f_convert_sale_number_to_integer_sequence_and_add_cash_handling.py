"""convert_sale_number_to_integer_sequence_and_add_cash_handling

Revision ID: e09d0a09bc6f
Revises: 9f6eb2dc0e9b
Create Date: 2026-11-20 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e09d0a09bc6f"
down_revision: str | Sequence[str] | None = "9f6eb2dc0e9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add cash handling and convert sale_number to integer."""
    # 1. Agregar campos de manejo de efectivo
    op.add_column(
        "commerce_sale",
        sa.Column(
            "amount_tendered",
            sa.Float(),
            nullable=True,
            comment="Monto entregado por el cliente en efectivo",
        ),
    )
    op.add_column(
        "commerce_sale",
        sa.Column(
            "change_given",
            sa.Float(),
            nullable=True,
            comment="Cambio o vuelto devuelto al cliente",
        ),
    )

    # 2. Convertir sale_number a Integer con secuencia atómica
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            WITH numbered AS (
                SELECT id,
                       COALESCE(
                           sheet_sale_id,
                           NULLIF(
                               SUBSTRING(REGEXP_REPLACE(sale_number, '\\D', '', 'g')
                               FROM 1 FOR 9), ''
                           )::integer,
                           ROW_NUMBER() OVER (
                               ORDER BY COALESCE(sale_date, created_at), id
                           )
                       ) as assigned_num
                FROM commerce_sale
            )
            UPDATE commerce_sale
            SET sale_number = numbered.assigned_num::text
            FROM numbered
            WHERE commerce_sale.id = numbered.id;
        """)
        op.alter_column(
            "commerce_sale",
            "sale_number",
            existing_type=sa.String(length=50),
            type_=sa.Integer(),
            postgresql_using="sale_number::integer",
            nullable=False,
        )
        op.execute("""
            CREATE SEQUENCE IF NOT EXISTS commerce_sale_sale_number_seq;
            SELECT setval(
                'commerce_sale_sale_number_seq',
                GREATEST(COALESCE((SELECT MAX(sale_number) FROM commerce_sale), 1), 1),
                (SELECT MAX(sale_number) FROM commerce_sale) IS NOT NULL
            );
            ALTER TABLE commerce_sale
            ALTER COLUMN sale_number
            SET DEFAULT nextval('commerce_sale_sale_number_seq');
        """)
    else:
        with op.batch_alter_table("commerce_sale") as batch_op:
            batch_op.alter_column(
                "sale_number",
                existing_type=sa.String(length=50),
                type_=sa.Integer(),
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            ALTER TABLE commerce_sale ALTER COLUMN sale_number DROP DEFAULT;
            DROP SEQUENCE IF EXISTS commerce_sale_sale_number_seq;
        """)
        op.alter_column(
            "commerce_sale",
            "sale_number",
            existing_type=sa.Integer(),
            type_=sa.String(length=50),
            postgresql_using="sale_number::text",
            nullable=False,
        )
    else:
        with op.batch_alter_table("commerce_sale") as batch_op:
            batch_op.alter_column(
                "sale_number",
                existing_type=sa.Integer(),
                type_=sa.String(length=50),
            )

    op.drop_column("commerce_sale", "change_given")
    op.drop_column("commerce_sale", "amount_tendered")
