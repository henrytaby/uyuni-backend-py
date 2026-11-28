"""add_unaccent_and_rebuild_pg_trgm_search_indexes

Revision ID: f6c115453a45
Revises: f684fc5e7bf2
Create Date: 2026-11-28 12:03:42.992772

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6c115453a45"
down_revision: str | Sequence[str] | None = "f684fc5e7bf2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRODUCT_MASTER_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_commerce_product_master_code_trgm", "code"),
    ("ix_commerce_product_master_name_trgm", "name"),
    ("ix_commerce_product_master_brand_trgm", "brand"),
    ("ix_commerce_product_master_model_trgm", "model"),
    ("ix_commerce_product_master_description_trgm", "description"),
    ("ix_commerce_product_master_features_trgm", "features"),
)

_PRODUCT_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_commerce_product_variant_name_trgm", "variant_name"),
    ("ix_commerce_product_status_trgm", "status"),
    ("ix_commerce_product_physical_condition_trgm", "physical_condition"),
    ("ix_commerce_product_defect_detail_trgm", "defect_detail"),
)

_SALE_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_commerce_sale_customer_name_trgm", "customer_name"),
    ("ix_commerce_sale_channel_trgm", "channel"),
    ("ix_commerce_sale_payment_method_trgm", "payment_method"),
    ("ix_commerce_sale_payment_status_trgm", "payment_status"),
    ("ix_commerce_sale_delivery_status_trgm", "delivery_status"),
    ("ix_commerce_sale_delivery_address_trgm", "delivery_address"),
    ("ix_commerce_sale_observations_trgm", "observations"),
)

_ALL_UNACCENT_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("commerce_product_master", _PRODUCT_MASTER_INDEXES),
    ("commerce_product", _PRODUCT_INDEXES),
    ("commerce_sale", _SALE_INDEXES),
)


def upgrade() -> None:
    """Enable unaccent, create immutable_unaccent, and rebuild GIN trgm indexes."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        DO $$
        DECLARE
            ext_schema text;
        BEGIN
            SELECT n.nspname INTO ext_schema
            FROM pg_extension e
            JOIN pg_namespace n ON n.oid = e.extnamespace
            WHERE e.extname = 'unaccent';

            EXECUTE format(
                'CREATE OR REPLACE FUNCTION immutable_unaccent(text) '
                'RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS '
                '$f$ SELECT %I.unaccent(%L::regdictionary, $1); $f$',
                ext_schema,
                format('%I.unaccent', ext_schema)
            );
        END $$
        """
    )

    for table_name, indexes in _ALL_UNACCENT_GROUPS:
        for index_name, column_name in indexes:
            op.drop_index(index_name, table_name=table_name, if_exists=True)
            op.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} USING gin "
                f"(immutable_unaccent({column_name}) gin_trgm_ops)"
            )


def downgrade() -> None:
    """Restore raw pg_trgm GIN indexes and drop immutable_unaccent."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name, indexes in reversed(_ALL_UNACCENT_GROUPS):
        for index_name, _ in reversed(indexes):
            op.drop_index(index_name, table_name=table_name, if_exists=True)

    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")

    for table_name, indexes in (
        ("commerce_product_master", _PRODUCT_MASTER_INDEXES),
        ("commerce_product", _PRODUCT_INDEXES),
    ):
        for index_name, column_name in indexes:
            op.create_index(
                index_name,
                table_name,
                [column_name],
                unique=False,
                if_not_exists=True,
                postgresql_using="gin",
                postgresql_ops={column_name: "gin_trgm_ops"},
            )
