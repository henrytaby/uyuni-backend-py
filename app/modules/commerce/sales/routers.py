from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.sales.schemas import (
    AvailableProductForSale,
    SaleCreate,
    SaleFilterParams,
    SaleListQuery,
    SaleRead,
    SaleUpdate,
)
from app.modules.commerce.sales.service import SaleService

router = APIRouter(prefix="/sales", tags=["Commerce - Sales"])


@router.post("/", response_model=SaleRead)
def create_sale(
    session: SessionDep,
    data: SaleCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = SaleService(session)
    return service.create(data)


@router.get("/", response_model=list[SaleRead])
def get_sales(
    session: SessionDep,
    query: Annotated[SaleListQuery, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SaleService(session)
    return service.get_all(
        offset=query.offset,
        limit=query.limit,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        search=query.search,
        filters=query,
    )


@router.get("/count")
def count_sales(
    session: SessionDep,
    query: Annotated[SaleFilterParams, Query()],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SaleService(session)
    return {"total": service.count(search=query.search, filters=query)}


@router.get("/available-products", response_model=list[AvailableProductForSale])
def get_available_products_for_sale(
    session: SessionDep,
    search: str | None = Query(
        None, description="Búsqueda por nombre, código o #item_number"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    """Catálogo rápido de productos con stock físico disponible para ventas."""
    service = SaleService(session)
    return service.get_available_products(search=search, limit=limit, offset=offset)


@router.get("/{id}", response_model=SaleRead)
def get_sale(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SaleService(session)
    sale = service.get_by_id(id)
    if not sale:
        raise NotFoundException(detail="Sale not found")
    return sale


@router.put("/{id}", response_model=SaleRead)
def update_sale(
    id: UUID,
    data: SaleUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = SaleService(session)
    sale = service.update(id, data.model_dump(exclude_unset=True))
    if not sale:
        raise NotFoundException(detail="Sale not found")
    return sale


@router.delete("/{id}")
def delete_sale(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = SaleService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Sale not found")
    return {"message": "Sale deleted successfully"}
