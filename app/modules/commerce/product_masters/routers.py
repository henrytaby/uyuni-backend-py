from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.schemas import (
    ProductMasterCreate,
    ProductMasterRead,
    ProductMasterUpdate,
)
from app.modules.commerce.product_masters.service import ProductMasterService

router = APIRouter(prefix="/product-masters", tags=["Commerce - Product Masters"])


def _enrich_master_read(
    master: ProductMaster, service: ProductMasterService
) -> ProductMasterRead:
    stock = service.get_stock_summary(master.id)
    return ProductMasterRead(
        id=master.id,
        item_number=master.item_number,
        code=master.code,
        name=master.name,
        description=master.description,
        category_id=master.category_id,
        live_basket_id=master.live_basket_id,
        brand=master.brand,
        model=master.model,
        official_price=master.official_price,
        minimum_price=master.minimum_price,
        published_price=master.published_price,
        currency=master.currency,
        cover_image_url=master.cover_image_url,
        marketplace_url=master.marketplace_url,
        external_info_url=master.external_info_url,
        features=master.features,
        marketing_details=master.marketing_details,
        is_reviewed=master.is_reviewed,
        is_fb_verified=master.is_fb_verified,
        has_video=master.has_video,
        is_published_marketplace=master.is_published_marketplace,
        is_whatsapp_published=master.is_whatsapp_published,
        is_active=master.is_active,
        total_available_stock=stock["available"],
        total_sold_stock=stock["sold"],
        total_merma_stock=stock["merma"],
    )


@router.post("/", response_model=ProductMasterRead)
def create_product_master(
    session: SessionDep,
    data: ProductMasterCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.CREATE,
        )
    ),
):
    service = ProductMasterService(session)
    payload = data.model_dump()
    master = service.create(ProductMaster(**payload))
    return _enrich_master_read(master, service)


@router.get("/", response_model=list[ProductMasterRead])
def get_product_masters(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc"),
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    live_basket_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    masters = service.get_all(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        category_id=category_id,
        live_basket_id=live_basket_id,
        is_active=is_active,
    )
    return [_enrich_master_read(m, service) for m in masters]


@router.get("/count")
def count_product_masters(
    session: SessionDep,
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    live_basket_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    count = service.count(
        search=search,
        category_id=category_id,
        live_basket_id=live_basket_id,
        is_active=is_active,
    )
    return {"total": count, "count": count}


@router.get("/by-number/{item_number}", response_model=ProductMasterRead)
def get_product_master_by_number(
    session: SessionDep,
    item_number: int,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    master = service.get_by_item_number(item_number)
    if not master:
        raise NotFoundException(f"Ficha maestra #{item_number} no encontrada")
    return _enrich_master_read(master, service)


@router.get("/resolve/{identifier}", response_model=ProductMasterRead)
def resolve_product_master(
    session: SessionDep,
    identifier: str,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    master = service.resolve_by_identifier(identifier)
    if not master:
        raise NotFoundException(
            f"No se encontró ficha maestra para el identificador '{identifier}'"
        )
    return _enrich_master_read(master, service)


@router.get("/{id}", response_model=ProductMasterRead)
def get_product_master_by_id(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    master = service.get_by_id(id)
    if not master:
        raise NotFoundException("Ficha maestra no encontrada")
    return _enrich_master_read(master, service)


@router.put("/{id}", response_model=ProductMasterRead)
def update_product_master(
    session: SessionDep,
    id: UUID,
    data: ProductMasterUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    updated = service.update(id, data.model_dump(exclude_unset=True))
    if not updated:
        raise NotFoundException("Ficha maestra no encontrada")
    return _enrich_master_read(updated, service)


@router.delete("/{id}")
def delete_product_master(
    session: SessionDep,
    id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ProductMasterService(session)
    success = service.delete(id)
    if not success:
        raise NotFoundException("Ficha maestra no encontrada")
    return {"message": "Ficha maestra eliminada exitosamente"}
