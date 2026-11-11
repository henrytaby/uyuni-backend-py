"""add commerce domain models

Revision ID: c0e81b83d91f
Revises: 5ab725ad6f8a
Create Date: 2026-11-07 19:07:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0e81b83d91f"
down_revision: Union[str, Sequence[str], None] = "5ab725ad6f8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. commerce_investment_round
    op.create_table(
        "commerce_investment_round",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("disbursement_date", sa.Date(), nullable=True),
        sa.Column(
            "capital_invested", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            nullable=False,
            server_default="BOB",
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "observations", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_investment_round_id"),
        "commerce_investment_round",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_investment_round_code"),
        "commerce_investment_round",
        ["code"],
        unique=True,
    )

    # 2. commerce_batch
    op.create_table(
        "commerce_batch",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("investment_round_id", sa.Uuid(), nullable=True),
        sa.Column(
            "provider", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True
        ),
        sa.Column(
            "batch_type", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True
        ),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("freight_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            nullable=False,
            server_default="BOB",
        ),
        sa.Column(
            "initial_items_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "merma_items_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "sellable_items_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "financial_status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="EN_RECUPERACION",
        ),
        sa.Column(
            "observations", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["investment_round_id"], ["commerce_investment_round.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_batch_id"), "commerce_batch", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_batch_code"), "commerce_batch", ["code"], unique=True
    )

    # 3. commerce_category
    op.create_table(
        "commerce_category",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("icon", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.Column(
            "typical_products",
            sqlmodel.sql.sqltypes.AutoString(length=1000),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_category_id"), "commerce_category", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_category_code"), "commerce_category", ["code"], unique=True
    )
    op.create_index(
        op.f("ix_commerce_category_name"), "commerce_category", ["name"], unique=False
    )

    # 4. commerce_live_basket
    op.create_table(
        "commerce_live_basket",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column(
            "label", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False
        ),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.Column(
            "price_range", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column(
            "target_audience",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_live_basket_id"),
        "commerce_live_basket",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_live_basket_code"),
        "commerce_live_basket",
        ["code"],
        unique=True,
    )

    # 5. commerce_channel
    op.create_table(
        "commerce_channel",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_channel_id"), "commerce_channel", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_channel_code"), "commerce_channel", ["code"], unique=True
    )
    op.create_index(
        op.f("ix_commerce_channel_name"), "commerce_channel", ["name"], unique=False
    )

    # 6. commerce_product_master
    op.create_table(
        "commerce_product_master",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_number", sa.Integer(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("live_basket_id", sa.Uuid(), nullable=True),
        sa.Column(
            "brand", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True
        ),
        sa.Column(
            "model", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=True
        ),
        sa.Column("official_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("minimum_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("published_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            nullable=False,
            server_default="BOB",
        ),
        sa.Column(
            "cover_image_url",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column(
            "marketplace_url",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column(
            "external_info_url",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column(
            "features", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column(
            "marketing_details",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column(
            "is_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_fb_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "has_video", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_published_marketplace",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_whatsapp_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["commerce_category.id"]),
        sa.ForeignKeyConstraint(["live_basket_id"], ["commerce_live_basket.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_product_master_id"),
        "commerce_product_master",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_master_item_number"),
        "commerce_product_master",
        ["item_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commerce_product_master_code"),
        "commerce_product_master",
        ["code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commerce_product_master_name"),
        "commerce_product_master",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_master_category_id"),
        "commerce_product_master",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_master_live_basket_id"),
        "commerce_product_master",
        ["live_basket_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_master_is_active"),
        "commerce_product_master",
        ["is_active"],
        unique=False,
    )

    # 7. commerce_product
    op.create_table(
        "commerce_product",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_product_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("sheet_row_id", sa.Integer(), nullable=True),
        sa.Column(
            "variant_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column("cost_price", sa.Float(), nullable=True),
        sa.Column(
            "initial_quantity", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("sold_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("merma_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_quantity", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column(
            "physical_condition",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="OPERATIONAL",
        ),
        sa.Column(
            "defect_detail",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column(
            "is_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["master_product_id"], ["commerce_product_master.id"]
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["commerce_batch.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_product_id"), "commerce_product", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_product_master_product_id"),
        "commerce_product",
        ["master_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_batch_id"),
        "commerce_product",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_sheet_row_id"),
        "commerce_product",
        ["sheet_row_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_product_status"),
        "commerce_product",
        ["status"],
        unique=False,
    )

    # 8. commerce_sale
    op.create_table(
        "commerce_sale",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "sale_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column("sheet_sale_id", sa.Integer(), nullable=True),
        sa.Column("sale_date", sa.DateTime(), nullable=False),
        sa.Column(
            "customer_name",
            sqlmodel.sql.sqltypes.AutoString(length=150),
            nullable=False,
            server_default="Cliente Casual",
        ),
        sa.Column(
            "customer_phone",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=True,
        ),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column(
            "channel",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="Marketplace",
        ),
        sa.Column(
            "payment_method",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="QR",
        ),
        sa.Column(
            "payment_status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="COLLECTED",
        ),
        sa.Column(
            "delivery_modality",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=False,
            server_default="FREE_MEETING_POINT",
        ),
        sa.Column(
            "delivery_address",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
        sa.Column("delivery_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "delivery_cost_paid_by",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="FREE",
        ),
        sa.Column(
            "delivery_status",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="DELIVERED",
        ),
        sa.Column("total_collected", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_profit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            nullable=False,
            server_default="BOB",
        ),
        sa.Column(
            "observations", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["commerce_channel.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_sale_id"), "commerce_sale", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_sale_sale_number"),
        "commerce_sale",
        ["sale_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commerce_sale_sheet_sale_id"),
        "commerce_sale",
        ["sheet_sale_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_sale_sale_date"),
        "commerce_sale",
        ["sale_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_sale_channel_id"),
        "commerce_sale",
        ["channel_id"],
        unique=False,
    )

    # 9. commerce_sale_item
    op.create_table(
        "commerce_sale_item",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_margin", sa.Float(), nullable=False, server_default="0.0"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["commerce_sale.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["commerce_product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commerce_sale_item_id"), "commerce_sale_item", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_commerce_sale_item_sale_id"),
        "commerce_sale_item",
        ["sale_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commerce_sale_item_product_id"),
        "commerce_sale_item",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("commerce_sale_item")
    op.drop_table("commerce_sale")
    op.drop_table("commerce_product")
    op.drop_table("commerce_product_master")
    op.drop_table("commerce_channel")
    op.drop_table("commerce_live_basket")
    op.drop_table("commerce_category")
    op.drop_table("commerce_batch")
    op.drop_table("commerce_investment_round")
