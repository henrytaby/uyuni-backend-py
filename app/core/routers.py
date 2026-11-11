from fastapi import APIRouter

from app.auth import routers as Auth
from app.core.catalogs.routers import router as Catalogs
from app.modules.commerce import routers as Commerce
from app.modules.core import routers as Core
from app.modules.tasks import routers as Task

router = APIRouter()
# Core
router.include_router(Auth.router, prefix="/auth", tags=["Auth"])
# Global Catalogs
router.include_router(Catalogs)
# Modules
router.include_router(Task.router, prefix="/tasks", tags=["Tasks"])

# Core Domain (Unified Entry Point)
router.include_router(Core.router)

# Commerce Domain
router.include_router(Commerce.router)
