"""
Script de Migración y Unificación a Fichas Maestras (ProductMaster).

Convierte el inventario físico existente en commerce_product a un catálogo
maestro normalizado (commerce_product_master) con numeración limpia (1, 2, 53, 61...)
y unifica productos duplicados entre diferentes cajas/lotes:
  - NOV-053 (Ataúd 1) y NOV-165 (Ataúd 2) -> Ficha Maestra #53 (Almohadilla)
  - NOV-061 (Ataúd 1) y NOV-220 (Amazon Next) -> Ficha Maestra #61 (Lámpara 3D)

Uso:
    venv/bin/python scripts/migrate_to_product_masters.py
"""

import os
import sys

# Setup import path for the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from sqlmodel import Session, select

from app.core.db import engine
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product

logger = structlog.get_logger()

# Reglas de unificación de duplicados entre lotes
UNIFICATIONS = {
    # row_id_or_sku -> (target_item_number, variant_name)
    165: (53, "Modelo TK-HP2412"),
    220: (61, "Sistema Solar K9"),
}

PRIMARY_VARIANTS = {
    53: "Calor Seco y Húmedo",
    61: "Modelo Luna",
}


def run_migration():
    logger.info("Iniciando migración y unificación a commerce_product_master")

    with Session(engine) as session:
        # 1. Obtener todos los productos de inventario
        products = session.exec(select(Product).order_by(Product.sheet_row_id)).all()
        logger.info("Total de productos físicos en inventario", count=len(products))

        # Mapa de masters existentes en DB para idempotencia
        existing_masters = {
            m.item_number: m for m in session.exec(select(ProductMaster)).all()
        }

        # Separar productos primarios (que crean ficha) de los unificados
        primary_products: dict[int, Product] = {}
        for p in products:
            row_id = p.sheet_row_id or 0
            if row_id in UNIFICATIONS:
                continue
            primary_products[row_id] = p

        # 2. Crear o actualizar las fichas maestras primarias
        created_masters_count = 0
        masters_map: dict[int, ProductMaster] = {}

        for item_number, p in sorted(primary_products.items()):
            if item_number in existing_masters:
                master = existing_masters[item_number]
                master.is_published_marketplace = p.is_published_marketplace
                master.is_whatsapp_published = p.is_whatsapp_published
                master.is_fb_verified = p.is_fb_verified
                session.add(master)
            else:
                master = ProductMaster(
                    item_number=item_number,
                    code=str(item_number),
                    name=p.name,
                    description=p.features,
                    category_id=p.category_id,
                    brand=p.brand,
                    model=p.model,
                    official_price=p.official_price,
                    minimum_price=p.minimum_price,
                    published_price=p.published_price,
                    currency=p.currency,
                    cover_image_url=None,
                    features=p.features,
                    marketing_details=p.marketing_details,
                    is_reviewed=p.is_reviewed,
                    is_fb_verified=p.is_fb_verified,
                    has_video=p.has_video,
                    is_published_marketplace=p.is_published_marketplace,
                    is_whatsapp_published=p.is_whatsapp_published,
                    is_active=True,
                )
                session.add(master)
                session.flush()
                created_masters_count += 1

            masters_map[item_number] = master

        logger.info(
            "Fichas maestras procesadas",
            nuevas=created_masters_count,
            existentes=len(existing_masters),
            total_maestras=len(masters_map),
        )

        # 3. Vincular cada producto de inventario a su ficha maestra
        linked_count = 0
        unified_count = 0

        for p in products:
            row_id = p.sheet_row_id or 0

            # Si es un duplicado que debe unificarse
            if row_id in UNIFICATIONS:
                target_num, variant_desc = UNIFICATIONS[row_id]
                master = masters_map[target_num]
                p.master_product_id = master.id
                p.variant_name = variant_desc
                unified_count += 1
                logger.info(
                    "Producto unificado bajo ficha maestra existente",
                    sheet_row_id=row_id,
                    target_master=target_num,
                    variant=variant_desc,
                )
            else:
                master = masters_map[row_id]
                p.master_product_id = master.id
                if row_id in PRIMARY_VARIANTS:
                    p.variant_name = PRIMARY_VARIANTS[row_id]
                linked_count += 1

            session.add(p)

        session.commit()

        logger.info(
            "Migración finalizada con éxito",
            fichas_maestras=len(masters_map),
            items_vinculados_directos=linked_count,
            items_unificados=unified_count,
            total_items=len(products),
        )


if __name__ == "__main__":
    run_migration()
