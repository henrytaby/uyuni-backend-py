from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.core.constants import CoreModuleSlug
from app.modules.core.org_units.models import OrgUnit
from app.modules.core.org_units.schemas import OrgUnitCreate, OrgUnitRead, OrgUnitUpdate
from app.modules.core.org_units.service import OrgUnitService

router = APIRouter(prefix="/org-units", tags=["Core Staff - Org Units"])


@router.post("/", response_model=OrgUnitRead)
def create_org_unit(
    data: OrgUnitCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = OrgUnitService(session)
    return service.create(OrgUnit(**data.model_dump()))


@router.get("/", response_model=List[OrgUnitRead])
def get_org_units(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = OrgUnitService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_org_units(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = OrgUnitService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=OrgUnitRead)
def get_org_unit(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF, required_permission=PermissionAction.READ
        )
    ),
):
    service = OrgUnitService(session)
    org_unit = service.get_by_id(id)
    if not org_unit:
        raise HTTPException(status_code=404, detail="Org Unit not found")
    return org_unit


@router.patch("/{id}", response_model=OrgUnitRead)
def update_org_unit(
    id: UUID,
    data: OrgUnitUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = OrgUnitService(session)
    org_unit = service.update(id, data.model_dump(exclude_unset=True))
    if not org_unit:
        raise HTTPException(status_code=404, detail="Org Unit not found")
    return org_unit


@router.delete("/{id}")
def delete_org_unit(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.STAFF,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = OrgUnitService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Org Unit not found")
    return {"ok": True}
