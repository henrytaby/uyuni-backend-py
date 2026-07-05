from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.assets.acts.models import Act
from app.modules.assets.acts.schemas import ActCreate, ActRead, ActUpdate
from app.modules.assets.acts.service import ActService
from app.modules.assets.constants import AssetsModuleSlug

router = APIRouter(prefix="/acts", tags=["Assets - Acts"])


@router.post("/", response_model=ActRead)
def create_act(
    session: SessionDep,
    data: ActCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = ActService(session)
    return service.create(Act(**data.model_dump()))


@router.get("/", response_model=list[ActRead])
def get_acts(
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
    service = ActService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_acts(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ActService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=ActRead)
def get_act(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ActService(session)
    act = service.get_by_id(id)
    if not act:
        raise NotFoundException(detail="Act not found")
    return act


@router.patch("/{id}", response_model=ActRead)
def update_act(
    session: SessionDep,
    id: UUID,
    data: ActUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ActService(session)
    act = service.update(id, data.model_dump(exclude_unset=True))
    if not act:
        raise NotFoundException(detail="Act not found")
    return act


@router.delete("/{id}")
def delete_act(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=AssetsModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ActService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Act not found")
    return {"ok": True}
