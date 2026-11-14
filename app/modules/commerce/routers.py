"""
Módulo de enrutamiento unificado para el dominio Commerce.
Agrega los submódulos de rondas de inversión, lotes/cajas, categorías,
canastas para live, productos y transacciones de venta.
"""

from fastapi import APIRouter

from app.modules.commerce.assistant import router as assistant_router
from app.modules.commerce.batches import routers as batches_router
from app.modules.commerce.categories import routers as categories_router
from app.modules.commerce.channels import routers as channels_router
from app.modules.commerce.live_baskets import routers as live_baskets_router
from app.modules.commerce.product_masters import routers as product_masters_router
from app.modules.commerce.products import routers as products_router
from app.modules.commerce.rounds import routers as rounds_router
from app.modules.commerce.sales import routers as sales_router

router = APIRouter(prefix="/commerce")

# Agregación de submódulos de Commerce
router.include_router(assistant_router)
router.include_router(rounds_router.router)
router.include_router(batches_router.router)
router.include_router(categories_router.router)
router.include_router(channels_router.router)
router.include_router(product_masters_router.router)
router.include_router(live_baskets_router.router)
router.include_router(products_router.router)
router.include_router(sales_router.router)
