from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.assets.constants import AssetsModuleSlug
from app.modules.assets.institutions.models import Institution
from app.modules.assets.institutions.schemas import (
    InstitutionCreate,
    InstitutionRead,
    InstitutionUpdate,
)
from app.modules.assets.institutions.service import InstitutionService

router = APIRouter(prefix="/institutions", tags=["Assets - Institutions"])


@router.post("/", response_model=InstitutionRead)
def create_institution(
    data: InstitutionCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = InstitutionService(session)
    return service.create(Institution(**data.model_dump()))


@router.get("/", response_model=List[InstitutionRead])
def get_institutions(
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
    service = InstitutionService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_institutions(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = InstitutionService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=InstitutionRead)
def get_institution(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = InstitutionService(session)
    institution = service.get_by_id(id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@router.patch("/{id}", response_model=InstitutionRead)
def update_institution(
    id: UUID,
    data: InstitutionUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = InstitutionService(session)
    institution = service.update(id, data.model_dump(exclude_unset=True))
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@router.delete("/{id}")
def delete_institution(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = InstitutionService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Institution not found")
    return {"ok": True}
