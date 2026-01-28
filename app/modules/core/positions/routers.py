from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.core.positions.models import StaffPosition
from app.modules.core.positions.schemas import (
    StaffPositionCreate,
    StaffPositionRead,
    StaffPositionUpdate,
)
from app.modules.core.positions.service import StaffPositionService

router = APIRouter(prefix="/positions", tags=["Core Staff - Positions"])


@router.post("/", response_model=StaffPositionRead)
def create_position(
    data: StaffPositionCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.CREATE
        )
    ),
):
    service = StaffPositionService(session)
    return service.create(StaffPosition(**data.model_dump()))


@router.get("/", response_model=List[StaffPositionRead])
def get_positions(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffPositionService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_positions(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffPositionService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=StaffPositionRead)
def get_position(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffPositionService(session)
    position = service.get_by_id(id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


@router.patch("/{id}", response_model=StaffPositionRead)
def update_position(
    id: UUID,
    data: StaffPositionUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.UPDATE
        )
    ),
):
    service = StaffPositionService(session)
    position = service.update(id, data.model_dump(exclude_unset=True))
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


@router.delete("/{id}")
def delete_position(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug="core_staff", required_permission=PermissionAction.DELETE
        )
    ),
):
    service = StaffPositionService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Position not found")
    return {"ok": True}
