from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import get_session
from app.modules.assets.areas.models import Area
from app.modules.assets.areas.schemas import AreaCreate, AreaRead, AreaUpdate
from app.modules.assets.areas.service import AreaService
from app.modules.assets.constants import AssetsModuleSlug

router = APIRouter(prefix="/areas", tags=["Assets - Areas"])


@router.post("/", response_model=AreaRead)
def create_area(
    data: AreaCreate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = AreaService(session)
    return service.create(Area(**data.model_dump()))


@router.get("/", response_model=List[AreaRead])
def get_areas(
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
    service = AreaService(session)
    return service.get_all(offset, limit, sort_by, sort_order)


@router.get("/count")
def count_areas(
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = AreaService(session)
    return {"total": service.count()}


@router.get("/{id}", response_model=AreaRead)
def get_area(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = AreaService(session)
    area = service.get_by_id(id)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@router.patch("/{id}", response_model=AreaRead)
def update_area(
    id: UUID,
    data: AreaUpdate,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = AreaService(session)
    area = service.update(id, data.model_dump(exclude_unset=True))
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@router.delete("/{id}")
def delete_area(
    id: UUID,
    session: Session = Depends(get_session),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = AreaService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Area not found")
    return {"ok": True}
