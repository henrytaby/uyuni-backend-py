"""
Módulo de enrutamiento unificado para el dominio Assets.
Agrega los submódulos de instituciones, áreas, grupos, estados, actas y activos fijos.
"""

from fastapi import APIRouter

from app.modules.assets.acts import routers as acts_router
from app.modules.assets.areas import routers as areas_router
from app.modules.assets.assets import routers as assets_router
from app.modules.assets.groups import routers as groups_router
from app.modules.assets.institutions import routers as institutions_router
from app.modules.assets.statuses import routers as statuses_router

router = APIRouter(prefix="/assets")

# Agregación de submódulos de Assets
router.include_router(institutions_router.router)
router.include_router(areas_router.router)
router.include_router(groups_router.router)
router.include_router(statuses_router.router)
router.include_router(acts_router.router)
router.include_router(assets_router.router)
