from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.assets.groups.models import AssetGroup
from app.modules.assets.groups.schemas import (
    AssetGroupCreate,
    AssetGroupRead,
    AssetGroupUpdate,
)
from app.modules.assets.groups.service import AssetGroupService

router = APIRouter(prefix="/groups", tags=["Assets - Asset Groups"])


@router.post("/", response_model=AssetGroupRead)
def create_group(
    data: AssetGroupCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.CREATE
        )
    ),
):
    service = AssetGroupService(session)
    return service.create(AssetGroup(**data.model_dump()))


@router.get("/", response_model=List[AssetGroupRead])
def get_groups(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.READ
        )
    ),
):
    service = AssetGroupService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_groups(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.READ
        )
    ),
):
    service = AssetGroupService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=AssetGroupRead)
def get_group(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.READ
        )
    ),
):
    service = AssetGroupService(session)
    group = service.get_by_id(id)
    if not group:
        raise HTTPException(status_code=404, detail="Asset Group not found")
    return group


@router.patch("/{id}", response_model=AssetGroupRead)
def update_group(
    id: UUID,
    data: AssetGroupUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.UPDATE
        )
    ),
):
    service = AssetGroupService(session)
    group = service.update(id, data.model_dump(exclude_unset=True))
    if not group:
        raise HTTPException(status_code=404, detail="Asset Group not found")
    return group


@router.delete("/{id}")
def delete_group(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.DELETE
        )
    ),
):
    service = AssetGroupService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Asset Group not found")
    return {"ok": True}
