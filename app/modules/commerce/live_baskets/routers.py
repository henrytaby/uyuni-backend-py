from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.live_baskets.models import LiveBasket
from app.modules.commerce.live_baskets.schemas import (
    LiveBasketCreate,
    LiveBasketRead,
    LiveBasketUpdate,
)
from app.modules.commerce.live_baskets.service import LiveBasketService

router = APIRouter(prefix="/live-baskets", tags=["Commerce - Live Baskets"])


@router.post("/", response_model=LiveBasketRead)
def create_live_basket(
    session: SessionDep,
    data: LiveBasketCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = LiveBasketService(session)
    return service.create(LiveBasket(**data.model_dump()))


@router.get("/", response_model=list[LiveBasketRead])
def get_live_baskets(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = LiveBasketService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_live_baskets(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = LiveBasketService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=LiveBasketRead)
def get_live_basket(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = LiveBasketService(session)
    basket = service.get_by_id(id)
    if not basket:
        raise NotFoundException(detail="Live basket not found")
    return basket


@router.put("/{id}", response_model=LiveBasketRead)
def update_live_basket(
    id: UUID,
    data: LiveBasketUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = LiveBasketService(session)
    basket = service.update(id, data.model_dump(exclude_unset=True))
    if not basket:
        raise NotFoundException(detail="Live basket not found")
    return basket


@router.delete("/{id}")
def delete_live_basket(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = LiveBasketService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Live basket not found")
    return {"message": "Live basket deleted successfully"}
