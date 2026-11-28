from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.storage_locations.models import StorageLocation
from app.modules.commerce.storage_locations.schemas import (
    StorageLocationCreate,
    StorageLocationFilterParams,
    StorageLocationListQuery,
    StorageLocationRead,
    StorageLocationUpdate,
)
from app.modules.commerce.storage_locations.service import StorageLocationService

router = APIRouter(prefix="/storage-locations", tags=["Commerce - Storage Locations"])


@router.post("/", response_model=StorageLocationRead)
def create_storage_location(
    session: SessionDep,
    data: StorageLocationCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = StorageLocationService(session)
    return service.create(StorageLocation(**data.model_dump(mode="json")))


@router.get("/", response_model=list[StorageLocationRead])
def get_storage_locations(
    session: SessionDep,
    query: Annotated[StorageLocationListQuery, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = StorageLocationService(session)
    return service.get_all(
        offset=query.offset,
        limit=query.limit,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        search=query.search,
        filters=query,
    )


@router.get("/count")
def count_storage_locations(
    session: SessionDep,
    query: Annotated[StorageLocationFilterParams, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = StorageLocationService(session)
    return {"total": service.count(search=query.search, filters=query)}


@router.get("/{id}", response_model=StorageLocationRead)
def get_storage_location(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = StorageLocationService(session)
    location = service.get_by_id(id)
    if not location:
        raise NotFoundException(detail="Storage location not found")
    return location


@router.put("/{id}", response_model=StorageLocationRead)
def update_storage_location(
    id: UUID,
    data: StorageLocationUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = StorageLocationService(session)
    location = service.update(id, data.model_dump(mode="json", exclude_unset=True))
    if not location:
        raise NotFoundException(detail="Storage location not found")
    return location


@router.delete("/{id}")
def delete_storage_location(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = StorageLocationService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Storage location not found")
    return {"message": "Storage location deleted successfully"}
