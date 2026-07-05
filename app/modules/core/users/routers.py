from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.modules.core.constants import CoreModuleSlug
from app.modules.core.users.schemas import (
    UserCreate,
    UserRead,
    UserReadDetailed,
    UserUpdate,
)
from app.modules.core.users.service import UserService

router = APIRouter(prefix="/users", tags=["Core Staff - Users"])


@router.post("/", response_model=UserRead)
def create_user(
    session: SessionDep,
    data: UserCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = UserService(session)
    # Extract password to pass separately to service
    user_dict = data.model_dump(exclude={"password"})
    user_obj = User(**user_dict)
    return service.create(user_obj, data.password)


@router.get("/", response_model=list[UserReadDetailed])
def get_users_list(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    is_superuser: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return service.get_all(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        is_active=is_active,
        is_superuser=is_superuser,
    )


@router.get("/count")
def count_users(
    session: SessionDep,
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    is_superuser: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return {
        "total": service.count(
            search=search,
            is_active=is_active,
            is_superuser=is_superuser,
        )
    }


@router.get("/{id}", response_model=UserReadDetailed)
def get_user(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    user = service.get_by_id(id)
    if not user:
        raise NotFoundException(detail="User not found")
    return user


@router.patch("/{id}", response_model=UserRead)
def update_user(
    session: SessionDep,
    id: UUID,
    data: UserUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = UserService(session)
    # Filter only provided fields to update
    update_data = data.model_dump(exclude_unset=True)
    user = service.update(id, update_data)
    if not user:
        raise NotFoundException(detail="User not found")
    return user


@router.delete("/{id}")
def delete_user(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = UserService(session)
    if not service.delete(id):
        raise NotFoundException(detail="User not found")
    return {"ok": True}
