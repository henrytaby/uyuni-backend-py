"""add_pg_trgm_search_indexes_for_commerce

Revision ID: f684fc5e7bf2
Revises: 8ab2702d56f1
Create Date: 2026-11-28 11:55:07.976243

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f684fc5e7bf2"
down_revision: str | Sequence[str] | None = "8ab2702d56f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRODUCT_MASTER_TRGM_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_commerce_product_master_code_trgm", "code"),
    ("ix_commerce_product_master_name_trgm", "name"),
    ("ix_commerce_product_master_brand_trgm", "brand"),
    ("ix_commerce_product_master_model_trgm", "model"),
    ("ix_commerce_product_master_description_trgm", "description"),
    ("ix_commerce_product_master_features_trgm", "features"),
)

_PRODUCT_TRGM_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_commerce_product_variant_name_trgm", "variant_name"),
    ("ix_commerce_product_status_trgm", "status"),
    ("ix_commerce_product_physical_condition_trgm", "physical_condition"),
    ("ix_commerce_product_defect_detail_trgm", "defect_detail"),
)


def upgrade() -> None:
    """Enable pg_trgm and create GIN trigram indexes for commerce search."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    for index_name, column_name in _PRODUCT_MASTER_TRGM_INDEXES:
        op.create_index(
            index_name,
            "commerce_product_master",
            [column_name],
            unique=False,
            if_not_exists=True,
            postgresql_using="gin",
            postgresql_ops={column_name: "gin_trgm_ops"},
        )

    for index_name, column_name in _PRODUCT_TRGM_INDEXES:
        op.create_index(
            index_name,
            "commerce_product",
            [column_name],
            unique=False,
            if_not_exists=True,
            postgresql_using="gin",
            postgresql_ops={column_name: "gin_trgm_ops"},
        )


def downgrade() -> None:
    """Drop GIN trigram indexes for commerce search."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for index_name, _ in reversed(_PRODUCT_TRGM_INDEXES):
        op.drop_index(
            index_name,
            table_name="commerce_product",
            if_exists=True,
        )

    for index_name, _ in reversed(_PRODUCT_MASTER_TRGM_INDEXES):
        op.drop_index(
            index_name,
            table_name="commerce_product_master",
            if_exists=True,
        )
