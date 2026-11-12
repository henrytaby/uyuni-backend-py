"""
Módulo de enrutamiento unificado para el dominio Core.
Agrega el submódulo de usuarios.
"""

from fastapi import APIRouter

from app.modules.core.media import routers as media_router
from app.modules.core.users import routers as users_router

router = APIRouter(prefix="/core")

# Agregación de submódulos de Core
router.include_router(users_router.router)
router.include_router(media_router.router)
