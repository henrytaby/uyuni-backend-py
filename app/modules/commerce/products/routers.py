from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.products.models import Product
from app.modules.commerce.products.schemas import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from app.modules.commerce.products.service import ProductService

router = APIRouter(prefix="/products", tags=["Commerce - Products"])


@router.post("/", response_model=ProductRead)
def create_product(
    session: SessionDep,
    data: ProductCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = ProductService(session)
    return service.create(Product(**data.model_dump()))


@router.get("/", response_model=list[ProductRead])
def get_products(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    batch_id: UUID | None = Query(None),
    master_product_id: UUID | None = Query(None),
    status: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductService(session)
    return service.get_all(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        batch_id=batch_id,
        master_product_id=master_product_id,
        status=status,
    )


@router.get("/count")
def count_products(
    session: SessionDep,
    search: str | None = Query(None),
    batch_id: UUID | None = Query(None),
    master_product_id: UUID | None = Query(None),
    status: str | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductService(session)
    return {
        "total": service.count(
            search=search,
            batch_id=batch_id,
            master_product_id=master_product_id,
            status=status,
        )
    }


@router.get("/by-sku/{sku}", response_model=ProductRead)
def get_product_by_sku(
    sku: str,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductService(session)
    product = service.get_by_sku(sku)
    if not product:
        raise NotFoundException(detail="Product not found")
    return product


@router.get("/{id}", response_model=ProductRead)
def get_product(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductService(session)
    product = service.get_by_id(id)
    if not product:
        raise NotFoundException(detail="Product not found")
    return product


@router.put("/{id}", response_model=ProductRead)
def update_product(
    id: UUID,
    data: ProductUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductService(session)
    product = service.update(id, data.model_dump(exclude_unset=True))
    if not product:
        raise NotFoundException(detail="Product not found")
    return product


@router.delete("/{id}")
def delete_product(
    id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ProductService(session)
    if not service.delete(id):
        raise NotFoundException(detail="Product not found")
    return {"message": "Product deleted successfully"}
