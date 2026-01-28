from fastapi import APIRouter

from app.auth import routers as Auth
from app.modules.assets import routers as Assets
from app.modules.core import routers as Core
from app.modules.tasks import routers as Task

router = APIRouter()
# Core
router.include_router(Auth.router, prefix="/auth", tags=["Auth"])
# Modules
router.include_router(Task.router, prefix="/tasks", tags=["Tasks"])

# Core Domain (Unified Entry Point)
router.include_router(Core.router)

# Assets
router.include_router(Assets.router)
