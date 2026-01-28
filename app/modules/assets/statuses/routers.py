from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.assets.statuses.models import AssetStatus
from app.modules.assets.statuses.schemas import (
    AssetStatusCreate,
    AssetStatusRead,
    AssetStatusUpdate,
)
from app.modules.assets.statuses.service import AssetStatusService

router = APIRouter(prefix="/statuses", tags=["Assets - Asset Statuses"])


@router.post("/", response_model=AssetStatusRead)
def create_status(
    data: AssetStatusCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.CREATE
        )
    ),
):
    service = AssetStatusService(session)
    return service.create(AssetStatus(**data.model_dump()))


@router.get("/", response_model=List[AssetStatusRead])
def get_statuses(
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
    service = AssetStatusService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_statuses(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.READ
        )
    ),
):
    service = AssetStatusService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=AssetStatusRead)
def get_status(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.READ
        )
    ),
):
    service = AssetStatusService(session)
    status = service.get_by_id(id)
    if not status:
        raise HTTPException(status_code=404, detail="Asset Status not found")
    return status


@router.patch("/{id}", response_model=AssetStatusRead)
def update_status(
    id: UUID,
    data: AssetStatusUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.UPDATE
        )
    ),
):
    service = AssetStatusService(session)
    status = service.update(id, data.model_dump(exclude_unset=True))
    if not status:
        raise HTTPException(status_code=404, detail="Asset Status not found")
    return status


@router.delete("/{id}")
def delete_status(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="assets", required_permission=PermissionAction.DELETE
        )
    ),
):
    service = AssetStatusService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Asset Status not found")
    return {"ok": True}
