from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.core.constants import CoreModuleSlug
from app.modules.core.staff.models import Staff
from app.modules.core.staff.schemas import StaffCreate, StaffRead, StaffUpdate
from app.modules.core.staff.service import StaffService

router = APIRouter(prefix="/staff", tags=["Core Staff - Personal"])


@router.post("/", response_model=StaffRead)
def create_staff(
    data: StaffCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = StaffService(session)
    return service.create(Staff(**data.model_dump()))


@router.get("/", response_model=List[StaffRead])
def get_staff_list(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_staff(
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=StaffRead)
def get_staff(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    staff = service.get_by_id(id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.patch("/{id}", response_model=StaffRead)
def update_staff(
    id: UUID,
    data: StaffUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = StaffService(session)
    staff = service.update(id, data.model_dump(exclude_unset=True))
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.delete("/{id}")
def delete_staff(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = StaffService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"ok": True}
