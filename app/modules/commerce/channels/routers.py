from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.channels.models import SalesChannel
from app.modules.commerce.channels.schemas import (
    SalesChannelCreate,
    SalesChannelRead,
    SalesChannelUpdate,
)
from app.modules.commerce.channels.service import SalesChannelService
from app.modules.commerce.constants import CommerceModuleSlug

router = APIRouter(prefix="/channels", tags=["Commerce - Sales Channels"])


@router.post("/", response_model=SalesChannelRead)
def create_channel(
    session: SessionDep,
    data: SalesChannelCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = SalesChannelService(session)
    return service.create(SalesChannel(**data.model_dump()))


@router.get("/", response_model=list[SalesChannelRead])
def get_channels(
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
    service = SalesChannelService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_channels(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SalesChannelService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=SalesChannelRead)
def get_channel(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SalesChannelService(session)
    channel = service.get_by_id(id)
    if not channel:
        raise NotFoundException(detail="Sales Channel not found")
    return channel


@router.put("/{id}", response_model=SalesChannelRead)
def update_channel(
    id: UUID,
    data: SalesChannelUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = SalesChannelService(session)
    channel = service.update(id, data.model_dump(exclude_unset=True))
    if not channel:
        raise NotFoundException(detail="Sales Channel not found")
    return channel


@router.delete("/{id}")
def delete_channel(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = SalesChannelService(session)
    success = service.delete(id)
    if not success:
        raise NotFoundException(detail="Sales Channel not found")
    return {"ok": True}
