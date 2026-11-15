from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.product_masters.schemas import (
    ProductMasterImageBulkDelete,
    ProductMasterImageRead,
    ProductMasterImageReorderItem,
    ProductMasterImageUpdate,
)
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


@router.get("/{id}/images", response_model=list[ProductMasterImageRead])
def get_product_images(
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
    images = service.get_images(id)
    return [ProductMasterImageRead.model_validate(img) for img in images]


@router.post("/{id}/images", response_model=list[ProductMasterImageRead])
async def upload_product_images(
    id: UUID,
    session: SessionDep,
    files: list[UploadFile] = File(
        ..., description="Archivos de fotos reales tomadas en almacén"
    ),
    is_public: bool = Form(
        default=False,
        description="¿Publicar en catálogo web público? (Por defecto False)",
    ),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductService(session)
    files_data = []
    for f in files:
        content = await f.read()
        files_data.append(
            {
                "content": content,
                "filename": f.filename or "real_product.webp",
                "content_type": f.content_type or "image/jpeg",
            }
        )
    created = service.add_images(id, files_data, is_public=is_public)
    return [ProductMasterImageRead.model_validate(img) for img in created]


@router.put("/{id}/images/reorder", response_model=list[ProductMasterImageRead])
def reorder_product_images(
    id: UUID,
    items: list[ProductMasterImageReorderItem],
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductService(session)
    images = service.reorder_images(id, items)
    return [ProductMasterImageRead.model_validate(img) for img in images]


@router.patch("/{id}/images/{image_id}", response_model=ProductMasterImageRead)
def update_product_image(
    id: UUID,
    image_id: UUID,
    data: ProductMasterImageUpdate,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductService(session)
    img = service.update_image(id, image_id, data)
    return ProductMasterImageRead.model_validate(img)


@router.delete("/{id}/images/{image_id}")
def delete_product_image(
    id: UUID,
    image_id: UUID,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ProductService(session)
    service.delete_image(id, image_id)
    return {"message": "Fotografía eliminada correctamente"}


@router.post("/{id}/images/bulk-delete")
def bulk_delete_product_images(
    id: UUID,
    data: ProductMasterImageBulkDelete,
    session: SessionDep,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ProductService(session)
    count = service.delete_images_bulk(id, data.image_ids)
    return {
        "message": f"{count} fotografías eliminadas correctamente",
        "deleted_count": count,
    }
