from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.assets.assets.models import FixedAsset
from app.modules.assets.assets.schemas import (
    FixedAssetCreate,
    FixedAssetRead,
    FixedAssetUpdate,
)
from app.modules.assets.assets.service import FixedAssetService
from app.modules.assets.constants import AssetsModuleSlug

router = APIRouter(prefix="/assets", tags=["Assets - Fixed Assets"])


@router.post("/", response_model=FixedAssetRead)
def create_asset(
    session: SessionDep,
    data: FixedAssetCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = FixedAssetService(session)
    return service.create(FixedAsset(**data.model_dump()))


@router.get("/", response_model=list[FixedAssetRead])
def get_assets(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = FixedAssetService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_assets(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = FixedAssetService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=FixedAssetRead)
def get_asset(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = FixedAssetService(session)
    asset = service.get_by_id(id)
    if not asset:
        raise NotFoundException(detail="Asset not found")
    return asset


@router.patch("/{id}", response_model=FixedAssetRead)
def update_asset(
    session: SessionDep,
    id: UUID,
    data: FixedAssetUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = FixedAssetService(session)
    asset = service.update(id, data.model_dump(exclude_unset=True))
    if not asset:
        raise NotFoundException(detail="Asset not found")
    return asset


@router.delete("/{id}")
def delete_asset(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = FixedAssetService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Asset not found")
    return {"ok": True}
