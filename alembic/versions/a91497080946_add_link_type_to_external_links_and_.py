"""add_link_type_to_external_links_and_migrate_marketplace_url

Revision ID: a91497080946
Revises: eaeab392e502
Create Date: 2026-11-13 20:10:09.726015

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.sql import column, table

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a91497080946"
down_revision: Union[str, Sequence[str], None] = "eaeab392e502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def detect_mkt_portal(url: str) -> tuple[str, str]:
    """Clasifica portal y etiqueta para enlaces de marketplace / publicación."""
    cleaned = (url or "").lower()
    if "facebook.com" in cleaned or "fb.com" in cleaned or "fb.me" in cleaned:
        return "FACEBOOK", "Facebook Marketplace"
    if "mercadolibre" in cleaned:
        return "MERCADOLIBRE", "MercadoLibre Publicación"
    if "instagram.com" in cleaned:
        return "INSTAGRAM", "Instagram"
    if "tiktok.com" in cleaned:
        return "TIKTOK", "TikTok Shop"
    if "wa.me" in cleaned or "whatsapp.com" in cleaned:
        return "WHATSAPP", "WhatsApp"
    return "OTHER", "Publicación Marketplace"


def upgrade() -> None:
    """Añade link_type a external_links, migra marketplace_url y la elimina."""
    # 1. Añadir columna link_type con default 'REFERENCE'
    op.add_column(
        "commerce_product_master_external_link",
        sa.Column(
            "link_type",
            sa.String(length=20),
            server_default="REFERENCE",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_commerce_product_master_external_link_link_type"),
        "commerce_product_master_external_link",
        ["link_type"],
        unique=False,
    )

    # 2. Migrar los marketplace_url existentes a la tabla de enlaces externos
    conn = op.get_bind()

    master_table = table(
        "commerce_product_master",
        column("id", sa.UUID),
        column("marketplace_url", sa.String),
        column("is_published_marketplace", sa.Boolean),
    )

    external_link_table = table(
        "commerce_product_master_external_link",
        column("id", sa.UUID),
        column("created_at", sa.DateTime),
        column("updated_at", sa.DateTime),
        column("created_by_id", sa.UUID),
        column("updated_by_id", sa.UUID),
        column("product_master_id", sa.UUID),
        column("url", sa.String),
        column("portal", sa.String),
        column("label", sa.String),
        column("link_type", sa.String),
        column("is_primary", sa.Boolean),
        column("is_public", sa.Boolean),
        column("sort_order", sa.Integer),
    )

    select_stmt = sa.select(
        master_table.c.id,
        master_table.c.marketplace_url,
    ).where(
        master_table.c.marketplace_url.isnot(None),
        master_table.c.marketplace_url != "",
    )

    results = conn.execute(select_stmt).fetchall()
    now = datetime.now(timezone.utc)

    migrated_count = 0
    for row in results:
        m_id, raw_url = row[0], row[1]
        if not raw_url:
            continue
        cleaned_url = raw_url.strip()
        if not (
            cleaned_url.startswith("http://") or cleaned_url.startswith("https://")
        ):
            continue

        portal, label = detect_mkt_portal(cleaned_url)

        conn.execute(
            external_link_table.insert().values(
                id=uuid.uuid7(),
                created_at=now,
                updated_at=now,
                created_by_id=None,
                updated_by_id=None,
                product_master_id=m_id,
                url=cleaned_url,
                portal=portal,
                label=label,
                link_type="MARKETPLACE",
                is_primary=True,
                is_public=True,
                sort_order=1,
            )
        )
        # Asegurar is_published_marketplace = True para productos con link
        conn.execute(
            master_table.update()
            .where(master_table.c.id == m_id)
            .values(is_published_marketplace=True)
        )
        migrated_count += 1

    print(f"Migrados {migrated_count} enlaces a external_link.")

    # 3. Eliminar la columna física marketplace_url de commerce_product_master
    op.drop_column("commerce_product_master", "marketplace_url")


def downgrade() -> None:
    """Restaura marketplace_url y elimina link_type."""
    # 1. Restaurar columna marketplace_url
    op.add_column(
        "commerce_product_master",
        sa.Column("marketplace_url", sa.String(length=500), nullable=True),
    )

    # 2. Respaldar URL primaria de MARKETPLACE de vuelta a commerce_product_master
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE commerce_product_master m
            SET marketplace_url = l.url
            FROM commerce_product_master_external_link l
            WHERE l.product_master_id = m.id
              AND l.link_type = 'MARKETPLACE'
              AND l.is_primary = true
        """)
    )

    # 3. Eliminar enlaces de MARKETPLACE
    conn.execute(
        sa.text(
            "DELETE FROM commerce_product_master_external_link "
            "WHERE link_type = 'MARKETPLACE'"
        )
    )

    # 4. Eliminar índice y columna link_type
    op.drop_index(
        op.f("ix_commerce_product_master_external_link_link_type"),
        table_name="commerce_product_master_external_link",
    )
    op.drop_column("commerce_product_master_external_link", "link_type")
