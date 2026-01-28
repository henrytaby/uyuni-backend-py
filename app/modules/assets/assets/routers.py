from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
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
    data: FixedAssetCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = FixedAssetService(session)
    return service.create(FixedAsset(**data.model_dump()))


@router.get("/", response_model=List[FixedAssetRead])
def get_assets(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = FixedAssetService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_assets(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = FixedAssetService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=FixedAssetRead)
def get_asset(
    id: UUID,
    session: Session = Depends(get_session),
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
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{id}", response_model=FixedAssetRead)
def update_asset(
    id: UUID,
    data: FixedAssetUpdate,
    session: Session = Depends(get_session),
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
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{id}")
def delete_asset(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = FixedAssetService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"ok": True}
