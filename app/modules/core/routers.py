"""
Módulo de enrutamiento unificado para el dominio Core.
Agrega los submódulos de unidades organizacionales, cargos y personal.
"""

from fastapi import APIRouter

# Importamos el módulo de catálogos de Core para disparar el auto-registro
import app.modules.core.catalogs  # noqa: F401
from app.modules.core.org_units import routers as org_units_router
from app.modules.core.positions import routers as positions_router
from app.modules.core.staff import routers as staff_personnel_router

router = APIRouter(prefix="/core")

# Agregación de submódulos de Core
router.include_router(org_units_router.router)
router.include_router(positions_router.router)
router.include_router(staff_personnel_router.router)
