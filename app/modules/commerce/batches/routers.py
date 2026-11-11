from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.batches.schemas import (
    BatchCreate,
    BatchRead,
    BatchUpdate,
)
from app.modules.commerce.batches.service import BatchService
from app.modules.commerce.constants import CommerceModuleSlug

router = APIRouter(prefix="/batches", tags=["Commerce - Batches & Boxes"])


@router.post("/", response_model=BatchRead)
def create_batch(
    session: SessionDep,
    data: BatchCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = BatchService(session)
    return service.create(Batch(**data.model_dump()))


@router.get("/", response_model=list[BatchRead])
def get_batches(
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
    service = BatchService(session)
    return service.get_all(offset, limit, sort_by, sort_order, search)


@router.get("/count")
def count_batches(
    session: SessionDep,
    search: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = BatchService(session)
    return {"total": service.count(search)}


@router.get("/{id}", response_model=BatchRead)
def get_batch(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = BatchService(session)
    batch = service.get_by_id(id)
    if not batch:
        raise NotFoundException(detail="Batch not found")
    return batch


@router.put("/{id}", response_model=BatchRead)
def update_batch(
    id: UUID,
    data: BatchUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = BatchService(session)
    batch = service.update(id, data.model_dump(exclude_unset=True))
    if not batch:
        raise NotFoundException(detail="Batch not found")
    return batch


@router.delete("/{id}")
def delete_batch(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = BatchService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Batch not found")
    return {"message": "Batch deleted successfully"}


@router.post("/{id}/recalculate", response_model=BatchRead)
def recalculate_batch(
    id: UUID,
    session: SessionDep,
    revalue_sales: bool = Query(
        True, description="Recalcular automáticamente costos y márgenes de ventas"
    ),
    force_product_counts: bool = Query(
        False, description="Forzar conteo exacto desde la tabla de productos"
    ),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = BatchService(session)
    batch = service.recalculate_from_products(
        id, revalue_sales=revalue_sales, force_product_counts=force_product_counts
    )
    if not batch:
        raise NotFoundException(detail="Batch not found")
    return batch


@router.post("/{id}/allocate-relative-costs", response_model=BatchRead)
def allocate_relative_costs(
    id: UUID,
    session: SessionDep,
    basis: str = Query(
        "official_price",
        description="Base de ponderación: 'official_price' o 'minimum_price'",
    ),
    revalue_sales: bool = Query(
        True, description="Recalcular automáticamente costos y márgenes de ventas"
    ),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = BatchService(session)
    batch = service.allocate_relative_costs(
        id, basis=basis, revalue_sales=revalue_sales
    )
    if not batch:
        raise NotFoundException(detail="Batch not found")
    return batch
