from typing import Annotated
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
    UserFilterParams,
    UserListQuery,
    UserLogLoginRead,
    UserReadDetailed,
    UserUpdate,
)
from app.modules.core.users.service import UserService

router = APIRouter(prefix="/users", tags=["Core - Users"])


@router.post("/", response_model=UserReadDetailed)
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
    # Extract password and role_slugs to pass separately to service
    user_dict = data.model_dump(exclude={"password", "role_slugs"})
    user_obj = User(**user_dict)
    return service.create(user_obj, data.password, role_slugs=data.role_slugs)


@router.get("/", response_model=list[UserReadDetailed])
def get_users_list(
    session: SessionDep,
    query: Annotated[UserListQuery, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return service.get_all(
        offset=query.offset,
        limit=query.limit,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        search=query.search,
        filters=query,
    )


@router.get("/count")
def count_users(
    session: SessionDep,
    query: Annotated[UserFilterParams, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return {"total": service.count(search=query.search, filters=query)}


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


@router.patch("/{id}", response_model=UserReadDetailed)
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


@router.post("/{id}/roles/{role_slug}", response_model=UserReadDetailed)
def assign_role_to_user(
    session: SessionDep,
    id: UUID,
    role_slug: str,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = UserService(session)
    user = service.assign_role(id, role_slug)
    if not user:
        raise NotFoundException(detail="User not found")
    return user


@router.delete("/{id}/roles/{role_slug}", response_model=UserReadDetailed)
def remove_role_from_user(
    session: SessionDep,
    id: UUID,
    role_slug: str,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = UserService(session)
    user = service.remove_role(id, role_slug)
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


@router.get("/{id}/logins", response_model=list[UserLogLoginRead])
def get_user_login_history(
    session: SessionDep,
    id: UUID,
    offset: int = 0,
    limit: int = 50,
    is_successful: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return service.get_login_history(
        user_id=id,
        offset=offset,
        limit=limit,
        is_successful=is_successful,
    )


@router.get("/{id}/logins/count")
def count_user_login_history(
    session: SessionDep,
    id: UUID,
    is_successful: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CoreModuleSlug.USERS,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = UserService(session)
    return {
        "total": service.count_login_history(
            user_id=id,
            is_successful=is_successful,
        )
    }
