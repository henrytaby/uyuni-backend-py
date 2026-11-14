"""create_commerce_product_external_link_table

Revision ID: d93fce7fce21
Revises: 6843e3c5c10e
Create Date: 2026-11-13 18:17:43.583417

"""

import re
from typing import Sequence, Union
from urllib.parse import urlparse
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = "d93fce7fce21"
down_revision: Union[str, Sequence[str], None] = "6843e3c5c10e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def detect_portal(url: str) -> tuple[str, str]:
    """Clasifica automáticamente el portal y genera una etiqueta legible."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        domain = ""

    if "amazon" in domain:
        tld = domain.split("amazon.")[-1].upper() if "amazon." in domain else ""
        label = f"Amazon {tld}" if tld and tld != "COM" else "Amazon"
        return "AMAZON", label
    elif "ebay" in domain:
        return "EBAY", "eBay"
    elif "alibaba" in domain:
        return "ALIBABA", "Alibaba"
    elif "aliexpress" in domain:
        return "ALIEXPRESS", "AliExpress"
    elif "walmart" in domain:
        return "WALMART", "Walmart"
    elif "mercadoli" in domain:
        return "MERCADOLIBRE", "MercadoLibre"
    elif "tiktok" in domain:
        return "TIKTOK", "TikTok"
    elif "youtube" in domain or "youtu.be" in domain:
        return "YOUTUBE", "YouTube"
    else:
        clean_domain = domain.replace("www.", "")
        return "OTHER", clean_domain or "Sitio Web"


def upgrade() -> None:
    """Crea tabla commerce_product_external_link y migra enlaces existentes."""
    op.create_table(
        "commerce_product_external_link",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("product_master_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column(
            "portal",
            sa.String(length=50),
            server_default="OTHER",
            nullable=False,
        ),
        sa.Column("label", sa.String(length=150), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_master_id"],
            ["commerce_product_master.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_commerce_product_external_link_product_master_id",
        "commerce_product_external_link",
        ["product_master_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_product_external_link_portal",
        "commerce_product_external_link",
        ["portal"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_product_external_link_is_primary",
        "commerce_product_external_link",
        ["is_primary"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_product_external_link_sort_order",
        "commerce_product_external_link",
        ["sort_order"],
        unique=False,
    )

    # Migración de datos existentes desde commerce_product_master
    conn = op.get_bind()
    masters = conn.execute(
        sa.text(
            "SELECT id, external_info_url FROM commerce_product_master "
            "WHERE external_info_url IS NOT NULL AND external_info_url != ''"
        )
    ).fetchall()

    link_table = table(
        "commerce_product_external_link",
        column("id", sa.UUID),
        column("product_master_id", sa.UUID),
        column("url", sa.String),
        column("portal", sa.String),
        column("label", sa.String),
        column("is_primary", sa.Boolean),
        column("sort_order", sa.Integer),
        column("created_at", sa.DateTime),
        column("updated_at", sa.DateTime),
    )

    for m_id, raw_url in masters:
        if not raw_url:
            continue
        extracted_urls = re.findall(r"https?://[^\s\"\'<>]+", raw_url.strip())
        for idx, u in enumerate(extracted_urls):
            portal_code, portal_label = detect_portal(u)
            conn.execute(
                link_table.insert().values(
                    id=uuid.uuid7(),
                    product_master_id=m_id,
                    url=u,
                    portal=portal_code,
                    label=portal_label,
                    is_primary=(idx == 0),
                    sort_order=idx + 1,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                )
            )


def downgrade() -> None:
    """Elimina índices y tabla commerce_product_external_link."""
    op.drop_index(
        "ix_commerce_product_external_link_sort_order",
        table_name="commerce_product_external_link",
    )
    op.drop_index(
        "ix_commerce_product_external_link_is_primary",
        table_name="commerce_product_external_link",
    )
    op.drop_index(
        "ix_commerce_product_external_link_portal",
        table_name="commerce_product_external_link",
    )
    op.drop_index(
        "ix_commerce_product_external_link_product_master_id",
        table_name="commerce_product_external_link",
    )
    op.drop_table("commerce_product_external_link")
