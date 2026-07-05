from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.core.constants import CoreModuleSlug
from app.modules.core.staff.models import Staff
from app.modules.core.staff.schemas import (
    StaffCreate,
    StaffRead,
    StaffReadDetailed,
    StaffUpdate,
)
from app.modules.core.staff.service import StaffService

router = APIRouter(prefix="/staff", tags=["Core Staff - Personal"])


@router.post("/", response_model=StaffRead)
def create_staff(
    session: SessionDep,
    data: StaffCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = StaffService(session)
    return service.create(Staff(**data.model_dump()))


@router.get("/", response_model=list[StaffReadDetailed])
def get_staff_list(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    org_unit_id: UUID | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    return service.get_all(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        is_active=is_active,
        org_unit_id=org_unit_id,
    )


@router.get("/count")
def count_staff(
    session: SessionDep,
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    org_unit_id: UUID | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    return {
        "total": service.count(
            search=search,
            is_active=is_active,
            org_unit_id=org_unit_id,
        )
    }


@router.get("/{id}", response_model=StaffReadDetailed)
def get_staff(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = StaffService(session)
    staff = service.get_by_id(id)
    if not staff:
        raise NotFoundException(detail="Staff not found")
    return staff


@router.patch("/{id}", response_model=StaffRead)
def update_staff(
    session: SessionDep,
    id: UUID,
    data: StaffUpdate,
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
        raise NotFoundException(detail="Staff not found")
    return staff


@router.delete("/{id}")
def delete_staff(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = StaffService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Staff not found")
    return {"ok": True}
