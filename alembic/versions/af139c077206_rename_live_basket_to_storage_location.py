"""rename_live_basket_to_storage_location

Revision ID: af139c077206
Revises: 469394d3c127
Create Date: 2026-11-28 09:38:05.139928

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af139c077206"
down_revision: str | Sequence[str] | None = "469394d3c127"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rename_pg_live_basket_constraints_and_indexes() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_live_basket_id "
        "RENAME TO ix_commerce_storage_location_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_live_basket_code "
        "RENAME TO ix_commerce_storage_location_code"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'commerce_live_basket_pkey'
            ) THEN
                ALTER TABLE commerce_storage_location
                    RENAME CONSTRAINT commerce_live_basket_pkey
                    TO commerce_storage_location_pkey;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'commerce_live_basket_created_by_id_fkey'
            ) THEN
                ALTER TABLE commerce_storage_location
                    RENAME CONSTRAINT commerce_live_basket_created_by_id_fkey
                    TO commerce_storage_location_created_by_id_fkey;
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'commerce_live_basket_updated_by_id_fkey'
            ) THEN
                ALTER TABLE commerce_storage_location
                    RENAME CONSTRAINT commerce_live_basket_updated_by_id_fkey
                    TO commerce_storage_location_updated_by_id_fkey;
            END IF;
        END $$;
        """
    )


def _rename_pg_product_master_fk_and_index() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_commerce_product_master_live_basket_id "
        "RENAME TO ix_commerce_product_master_storage_location_id"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'commerce_product_master_live_basket_id_fkey'
            ) THEN
                ALTER TABLE commerce_product_master
                    RENAME CONSTRAINT commerce_product_master_live_basket_id_fkey
                    TO commerce_product_master_storage_location_id_fkey;
            END IF;
        END $$;
        """
    )


def _upgrade_offline() -> None:
    op.rename_table("commerce_live_basket", "commerce_storage_location")
    _rename_pg_live_basket_constraints_and_indexes()

    op.add_column(
        "commerce_storage_location",
        sa.Column(
            "location_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'OTHER'"),
        ),
    )
    op.add_column(
        "commerce_storage_location",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute(
        """
        UPDATE commerce_storage_location
        SET location_type = CASE
            WHEN UPPER(code) = 'FONDO' THEN 'WAREHOUSE'
            WHEN UPPER(code) LIKE 'C%' THEN 'BASKET'
            ELSE 'OTHER'
        END
        """
    )
    op.create_index(
        "ix_commerce_storage_location_name",
        "commerce_storage_location",
        ["name"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_storage_location_location_type",
        "commerce_storage_location",
        ["location_type"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_storage_location_is_active",
        "commerce_storage_location",
        ["is_active"],
        unique=False,
    )
    op.drop_column("commerce_storage_location", "target_audience")
    op.drop_column("commerce_storage_location", "price_range")

    op.alter_column(
        "commerce_product_master",
        "live_basket_id",
        new_column_name="storage_location_id",
        existing_type=sa.Uuid(),
        existing_nullable=True,
    )
    _rename_pg_product_master_fk_and_index()


def upgrade() -> None:
    """Upgrade schema without data loss (resilient to pre-created empty table)."""
    if op.get_context().as_sql:
        _upgrade_offline()
        return

    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    has_live = "commerce_live_basket" in tables
    has_storage = "commerce_storage_location" in tables
    merged_into_existing_storage = False

    # 1. Resolver tabla commerce_live_basket -> commerce_storage_location
    if has_live and has_storage:
        # Si lifespan/create_all() pre-creó commerce_storage_location vacía,
        # la eliminamos para preservar intacta commerce_live_basket vía RENAME.
        existing_storage_count = bind.execute(
            sa.text("SELECT COUNT(*) FROM commerce_storage_location")
        ).scalar_one()
        if existing_storage_count == 0:
            op.drop_table("commerce_storage_location")
            has_storage = False
        else:
            # Si ya hubiera filas en commerce_storage_location, copiamos sin perder
            # datos y luego reasignamos referencias antes de borrar la vieja.
            if is_pg:
                op.execute(
                    """
                    INSERT INTO commerce_storage_location (
                        id, code, name, label, location_type, description,
                        is_active, created_at, updated_at,
                        created_by_id, updated_by_id
                    )
                    SELECT
                        id, code, name, label,
                        CASE
                            WHEN UPPER(code) = 'FONDO' THEN 'WAREHOUSE'
                            WHEN UPPER(code) LIKE 'C%' THEN 'BASKET'
                            ELSE 'OTHER'
                        END,
                        description, true, created_at, updated_at,
                        created_by_id, updated_by_id
                    FROM commerce_live_basket
                    ON CONFLICT DO NOTHING
                    """
                )
            else:
                op.execute(
                    """
                    INSERT OR IGNORE INTO commerce_storage_location (
                        id, code, name, label, location_type, description,
                        is_active, created_at, updated_at,
                        created_by_id, updated_by_id
                    )
                    SELECT
                        id, code, name, label,
                        CASE
                            WHEN UPPER(code) = 'FONDO' THEN 'WAREHOUSE'
                            WHEN UPPER(code) LIKE 'C%' THEN 'BASKET'
                            ELSE 'OTHER'
                        END,
                        description, 1, created_at, updated_at,
                        created_by_id, updated_by_id
                    FROM commerce_live_basket
                    """
                )
            merged_into_existing_storage = True

    if has_live and not has_storage:
        op.rename_table("commerce_live_basket", "commerce_storage_location")
        if is_pg:
            _rename_pg_live_basket_constraints_and_indexes()

    # 2. Asegurar columnas e índices estándar en commerce_storage_location
    inspector = sa.inspect(bind)
    storage_cols = {
        c["name"] for c in inspector.get_columns("commerce_storage_location")
    }
    storage_indexes = {
        idx["name"] for idx in inspector.get_indexes("commerce_storage_location")
    }

    if "location_type" not in storage_cols:
        op.add_column(
            "commerce_storage_location",
            sa.Column(
                "location_type",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'OTHER'"),
            ),
        )
    if "is_active" not in storage_cols:
        op.add_column(
            "commerce_storage_location",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )

    op.execute(
        """
        UPDATE commerce_storage_location
        SET location_type = CASE
            WHEN UPPER(code) = 'FONDO' THEN 'WAREHOUSE'
            WHEN UPPER(code) LIKE 'C%' THEN 'BASKET'
            ELSE 'OTHER'
        END
        WHERE location_type IS NULL OR location_type = 'OTHER'
        """
    )

    if "ix_commerce_storage_location_name" not in storage_indexes:
        op.create_index(
            "ix_commerce_storage_location_name",
            "commerce_storage_location",
            ["name"],
            unique=False,
        )
    if "ix_commerce_storage_location_location_type" not in storage_indexes:
        op.create_index(
            "ix_commerce_storage_location_location_type",
            "commerce_storage_location",
            ["location_type"],
            unique=False,
        )
    if "ix_commerce_storage_location_is_active" not in storage_indexes:
        op.create_index(
            "ix_commerce_storage_location_is_active",
            "commerce_storage_location",
            ["is_active"],
            unique=False,
        )

    if "target_audience" in storage_cols:
        op.drop_column("commerce_storage_location", "target_audience")
    if "price_range" in storage_cols:
        op.drop_column("commerce_storage_location", "price_range")

    # 3. Migrar FK en commerce_product_master: live_basket_id -> storage_location_id
    pm_cols = {c["name"] for c in inspector.get_columns("commerce_product_master")}
    pm_indexes = {
        idx["name"] for idx in inspector.get_indexes("commerce_product_master")
    }

    if "live_basket_id" in pm_cols and "storage_location_id" not in pm_cols:
        if merged_into_existing_storage and is_pg:
            op.execute(
                """
                ALTER TABLE commerce_product_master
                DROP CONSTRAINT IF EXISTS commerce_product_master_live_basket_id_fkey
                """
            )
        op.alter_column(
            "commerce_product_master",
            "live_basket_id",
            new_column_name="storage_location_id",
            existing_type=sa.Uuid(),
            existing_nullable=True,
        )
        if is_pg:
            if merged_into_existing_storage:
                op.create_foreign_key(
                    "commerce_product_master_storage_location_id_fkey",
                    "commerce_product_master",
                    "commerce_storage_location",
                    ["storage_location_id"],
                    ["id"],
                )
            _rename_pg_product_master_fk_and_index()
    elif "live_basket_id" in pm_cols and "storage_location_id" in pm_cols:
        op.execute(
            """
            UPDATE commerce_product_master
            SET storage_location_id = live_basket_id
            WHERE storage_location_id IS NULL AND live_basket_id IS NOT NULL
            """
        )
        if is_pg:
            op.execute(
                """
                ALTER TABLE commerce_product_master
                DROP CONSTRAINT IF EXISTS commerce_product_master_live_basket_id_fkey
                """
            )
        if "ix_commerce_product_master_live_basket_id" in pm_indexes:
            op.drop_index(
                "ix_commerce_product_master_live_basket_id",
                table_name="commerce_product_master",
            )
        op.drop_column("commerce_product_master", "live_basket_id")

    if merged_into_existing_storage:
        op.drop_table("commerce_live_basket")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'commerce_product_master_storage_location_id_fkey'
                ) THEN
                    ALTER TABLE commerce_product_master
                        RENAME CONSTRAINT
                            commerce_product_master_storage_location_id_fkey
                        TO commerce_product_master_live_basket_id_fkey;
                END IF;
            END $$
            """
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_commerce_product_master_storage_location_id "
            "RENAME TO ix_commerce_product_master_live_basket_id"
        )

    op.alter_column(
        "commerce_product_master",
        "storage_location_id",
        new_column_name="live_basket_id",
        existing_type=sa.Uuid(),
        existing_nullable=True,
    )

    op.add_column(
        "commerce_storage_location",
        sa.Column("price_range", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "commerce_storage_location",
        sa.Column("target_audience", sa.String(length=255), nullable=True),
    )

    op.drop_index(
        "ix_commerce_storage_location_is_active",
        table_name="commerce_storage_location",
    )
    op.drop_index(
        "ix_commerce_storage_location_location_type",
        table_name="commerce_storage_location",
    )
    op.drop_index(
        "ix_commerce_storage_location_name",
        table_name="commerce_storage_location",
    )

    op.drop_column("commerce_storage_location", "is_active")
    op.drop_column("commerce_storage_location", "location_type")

    if is_pg:
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'commerce_storage_location_updated_by_id_fkey'
                ) THEN
                    ALTER TABLE commerce_storage_location
                        RENAME CONSTRAINT commerce_storage_location_updated_by_id_fkey
                        TO commerce_live_basket_updated_by_id_fkey;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'commerce_storage_location_created_by_id_fkey'
                ) THEN
                    ALTER TABLE commerce_storage_location
                        RENAME CONSTRAINT commerce_storage_location_created_by_id_fkey
                        TO commerce_live_basket_created_by_id_fkey;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'commerce_storage_location_pkey'
                ) THEN
                    ALTER TABLE commerce_storage_location
                        RENAME CONSTRAINT commerce_storage_location_pkey
                        TO commerce_live_basket_pkey;
                END IF;
            END $$
            """
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_commerce_storage_location_code "
            "RENAME TO ix_commerce_live_basket_code"
        )
        op.execute(
            "ALTER INDEX IF EXISTS ix_commerce_storage_location_id "
            "RENAME TO ix_commerce_live_basket_id"
        )

    op.rename_table("commerce_storage_location", "commerce_live_basket")
