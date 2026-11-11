from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.sales.schemas import (
    SaleCreate,
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
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
    search: str | None = Query(None),
    channel: str | None = Query(None),
    payment_status: str | None = Query(None),
    delivery_status: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SaleService(session)
    return service.get_all(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        channel=channel,
        payment_status=payment_status,
        delivery_status=delivery_status,
    )


@router.get("/count")
def count_sales(
    session: SessionDep,
    search: str | None = Query(None),
    channel: str | None = Query(None),
    payment_status: str | None = Query(None),
    delivery_status: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = SaleService(session)
    return {
        "total": service.count(
            search=search,
            channel=channel,
            payment_status=payment_status,
            delivery_status=delivery_status,
        )
    }


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
