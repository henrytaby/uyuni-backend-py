from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.categories.models import Category
from app.modules.commerce.categories.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)
from app.modules.commerce.categories.service import CategoryService
from app.modules.commerce.constants import CommerceModuleSlug

router = APIRouter(prefix="/categories", tags=["Commerce - Categories"])


@router.post("/", response_model=CategoryRead)
def create_category(
    session: SessionDep,
    data: CategoryCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = CategoryService(session)
    return service.create(Category(**data.model_dump()))


@router.get("/", response_model=list[CategoryRead])
def get_categories(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = CategoryService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_categories(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = CategoryService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=CategoryRead)
def get_category(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = CategoryService(session)
    category = service.get_by_id(id)
    if not category:
        raise NotFoundException(detail="Category not found")
    return category


@router.put("/{id}", response_model=CategoryRead)
def update_category(
    id: UUID,
    data: CategoryUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = CategoryService(session)
    category = service.update(id, data.model_dump(exclude_unset=True))
    if not category:
        raise NotFoundException(detail="Category not found")
    return category


@router.delete("/{id}")
def delete_category(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = CategoryService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Category not found")
    return {"message": "Category deleted successfully"}
