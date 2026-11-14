from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlmodel import col, func, select

from app.auth.permissions import PermissionAction, PermissionChecker
from app.auth.schemas import UserModulePermission
from app.core.db import SessionDep
from app.core.exceptions import NotFoundException
from app.modules.commerce.constants import CommerceModuleSlug
from app.modules.commerce.product_masters.models import (
    ProductImage,
    ProductMaster,
    ProductMasterExternalLink,
)
from app.modules.commerce.product_masters.schemas import (
    ProductImageRead,
    ProductImageReorderItem,
    ProductImageUpdate,
    ProductMasterCreate,
    ProductMasterExternalLinkCreate,
    ProductMasterExternalLinkRead,
    ProductMasterExternalLinkReorderItem,
    ProductMasterExternalLinkUpdate,
    ProductMasterRead,
    ProductMasterUpdate,
)
from app.modules.commerce.product_masters.service import ProductMasterService

router = APIRouter(prefix="/product-masters", tags=["Commerce - Product Masters"])


def _enrich_master_read(
    master: ProductMaster,
    service: ProductMasterService,
    include_images: bool = False,
    include_links: bool = True,
) -> ProductMasterRead:
    stock = service.get_stock_summary(master.id)
    images_list: list[ProductImageRead] = []
    if include_images:
        db_images = service.get_images(master.id)
        images_list = [ProductImageRead.model_validate(img) for img in db_images]
        images_count = len(images_list)
    else:
        images_count = (
            service.session.exec(
                select(func.count(col(ProductImage.id))).where(
                    ProductImage.product_master_id == master.id
                )
            ).one()
            or 0
        )

    links_list: list[ProductMasterExternalLinkRead] = []
    if include_links:
        db_links = service.get_external_links(master.id)
        links_list = [
            ProductMasterExternalLinkRead.model_validate(link) for link in db_links
        ]
        links_count = len(links_list)
    else:
        links_count = (
            service.session.exec(
                select(func.count(col(ProductMasterExternalLink.id))).where(
                    ProductMasterExternalLink.product_master_id == master.id
                )
            ).one()
            or 0
        )

    # Separar en listas específicas por tipo
    ref_links = [
        lnk
        for lnk in links_list
        if getattr(lnk, "link_type", "REFERENCE") == "REFERENCE"
    ]
    mkt_links = [
        lnk
        for lnk in links_list
        if getattr(lnk, "link_type", "REFERENCE") == "MARKETPLACE"
    ]

    # Calcular URLs primarias al vuelo
    primary_ref = next((lnk for lnk in ref_links if lnk.is_primary), None)
    primary_mkt = next((lnk for lnk in mkt_links if lnk.is_primary), None)

    if not include_links and links_count > 0:
        db_primaries = service.session.exec(
            select(ProductMasterExternalLink).where(
                ProductMasterExternalLink.product_master_id == master.id,
                ProductMasterExternalLink.is_primary == True,  # noqa: E712
            )
        ).all()
        primary_ref_url = next(
            (p.url for p in db_primaries if p.link_type == "REFERENCE"), None
        )
        primary_mkt_url = next(
            (p.url for p in db_primaries if p.link_type == "MARKETPLACE"), None
        )
    else:
        primary_ref_url = primary_ref.url if primary_ref else None
        primary_mkt_url = primary_mkt.url if primary_mkt else None

    # Contadores específicos por tipo
    if include_links:
        ref_count = len(ref_links)
        mkt_count = len(mkt_links)
    else:
        ref_count = (
            service.session.exec(
                select(func.count(col(ProductMasterExternalLink.id))).where(
                    ProductMasterExternalLink.product_master_id == master.id,
                    ProductMasterExternalLink.link_type == "REFERENCE",
                )
            ).one()
            or 0
        )
        mkt_count = (
            service.session.exec(
                select(func.count(col(ProductMasterExternalLink.id))).where(
                    ProductMasterExternalLink.product_master_id == master.id,
                    ProductMasterExternalLink.link_type == "MARKETPLACE",
                )
            ).one()
            or 0
        )

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
        marketplace_url=primary_mkt_url,
        external_info_url=primary_ref_url,
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
        images=images_list,
        images_count=images_count,
        external_links=links_list,
        external_links_count=links_count,
        reference_links=ref_links,
        reference_links_count=ref_count,
        marketplace_links=mkt_links,
        marketplace_links_count=mkt_count,
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
    payload.pop("item_number", None)
    initial_url = payload.pop("external_info_url", None)
    initial_mkt_url = payload.pop("marketplace_url", None)
    master = service.create(
        ProductMaster(**payload),
        initial_external_url=initial_url,
        initial_marketplace_url=initial_mkt_url,
    )
    return _enrich_master_read(master, service, include_images=True)


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
    return [
        _enrich_master_read(m, service, include_images=False, include_links=False)
        for m in masters
    ]


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
    return _enrich_master_read(master, service, include_images=True)


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
    return _enrich_master_read(master, service, include_images=True)


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
    return _enrich_master_read(master, service, include_images=True)


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
    return _enrich_master_read(updated, service, include_images=True)


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


# =============================================================================
# ENDPOINTS MULTI-FOTOGRAFÍA Y GALERÍA (CLOUDINARY)
# =============================================================================


@router.post(
    "/{id}/images",
    response_model=list[ProductImageRead],
    summary="Subir lote de fotografías a Cloudinary para esta Ficha Maestra",
    description=(
        "Permite arrastrar y subir una o múltiples fotos simultáneamente "
        "(ej. 10+ fotos). Se optimizan automáticamente a WebP y se almacenan "
        "en la jerarquía: uyuni/products/{item_number}/{image_type}/"
    ),
)
async def upload_product_images(
    session: SessionDep,
    id: UUID,
    files: list[UploadFile] = File(
        ..., description="Archivos de imagen (JPG, PNG, WEBP, GIF, AVIF, máx 10MB)"
    ),
    image_type: str = Form(
        default="CATALOG",
        description="Categoría: CATALOG (web), REAL (almacén), MARKETING (banners)",
    ),
    is_cover: bool = Form(
        default=False,
        description="¿Establecer la primera imagen como foto de portada oficial?",
    ),
    product_id: UUID | None = Form(
        default=None,
        description="ID opcional del producto físico específico de inventario",
    ),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    files_data = []
    for f in files:
        content = await f.read()
        files_data.append(
            {
                "content": content,
                "filename": f.filename or "image.webp",
                "content_type": f.content_type or "image/jpeg",
            }
        )

    created = service.add_images(
        master_id=id,
        files_data=files_data,
        image_type=image_type,
        is_cover=is_cover,
        product_id=product_id,
    )
    return [ProductImageRead.model_validate(img) for img in created]


@router.get(
    "/{id}/images",
    response_model=list[ProductImageRead],
    summary="Listar galería de imágenes de la Ficha Maestra",
    description=(
        "Obtiene todas las imágenes asociadas ordenadas por sort_order y fecha."
    ),
)
def get_product_images(
    session: SessionDep,
    id: UUID,
    image_type: str | None = Query(
        None, description="Filtrar por tipo: CATALOG, REAL, MARKETING, BANNER"
    ),
    product_id: UUID | None = Query(
        None, description="Filtrar por unidad física específica de lote"
    ),
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
    images = service.get_images(id, image_type=image_type, product_id=product_id)
    return [ProductImageRead.model_validate(img) for img in images]


@router.patch(
    "/{id}/images/{image_id}/cover",
    response_model=ProductImageRead,
    summary="Definir fotografía como portada oficial de la Ficha Maestra",
    description=(
        "Marca la imagen como portada (is_cover=True), desmarca las demás "
        "y sincroniza cover_image_url."
    ),
)
def set_product_cover_image(
    session: SessionDep,
    id: UUID,
    image_id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    img = service.set_cover_image(id, image_id)
    return ProductImageRead.model_validate(img)


@router.put(
    "/{id}/images/reorder",
    response_model=list[ProductImageRead],
    summary="Reordenar la secuencia de imágenes de la galería (drag & drop)",
    description=(
        "Actualiza el sort_order de las imágenes según el nuevo orden establecido."
    ),
)
def reorder_product_images(
    session: SessionDep,
    id: UUID,
    items: list[ProductImageReorderItem],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    images = service.reorder_images(id, items)
    return [ProductImageRead.model_validate(img) for img in images]


@router.patch(
    "/{id}/images/{image_id}",
    response_model=ProductImageRead,
    summary="Actualizar metadatos de una fotografía",
    description="Modifica título descriptivo, tipo de imagen o activa como portada.",
)
def update_product_image(
    session: SessionDep,
    id: UUID,
    image_id: UUID,
    data: ProductImageUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    img = service.update_image(id, image_id, data)
    return ProductImageRead.model_validate(img)


@router.delete(
    "/{id}/images/{image_id}",
    summary="Eliminar fotografía de Cloudinary y de la base de datos",
    description=(
        "Destruye el asset en Cloudinary mediante su public_id y remueve el "
        "registro en la BD. Si la imagen era la portada oficial, reasigna "
        "automáticamente la siguiente foto disponible."
    ),
)
def delete_product_image(
    session: SessionDep,
    id: UUID,
    image_id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.DELETE,
        )
    ),
):
    service = ProductMasterService(session)
    service.delete_image(id, image_id)
    return {"message": "Fotografía eliminada exitosamente"}


# =========================================================================
# ENLACES EXTERNOS MULTI-PORTAL (/product-masters/{id}/links)
# =========================================================================


@router.post(
    "/{id}/links",
    response_model=ProductMasterExternalLinkRead,
    summary="Agregar enlace externo a ficha maestra",
    description=(
        "Registra un enlace de referencia técnica o comercial (Amazon, eBay, Alibaba, "
        "AliExpress, Walmart, YouTube, TikTok, MercadoLibre, etc.). Clasifica "
        "automáticamente el portal y genera etiqueta amigable si no se especifica. "
        "Permite definir si es público para el catálogo web o de uso interno."
    ),
)
def add_product_external_link(
    session: SessionDep,
    id: UUID,
    data: ProductMasterExternalLinkCreate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    link = service.add_external_link(
        master_id=id,
        url=data.url,
        link_type=data.link_type,
        label=data.label,
        is_primary=data.is_primary,
        is_public=data.is_public,
    )
    return ProductMasterExternalLinkRead.model_validate(link)


@router.get(
    "/{id}/links",
    response_model=list[ProductMasterExternalLinkRead],
    summary="Listar enlaces externos de una ficha maestra",
    description=(
        "Retorna los enlaces externos ordenados por sort_order. "
        "Soporta filtro only_public y link_type ('REFERENCE' o 'MARKETPLACE')."
    ),
)
def get_product_external_links(
    session: SessionDep,
    id: UUID,
    only_public: bool = Query(
        False, description="Filtrar solo enlaces visibles para catálogo público"
    ),
    link_type: str | None = Query(
        None, description="Filtrar por tipo de enlace ('REFERENCE' o 'MARKETPLACE')"
    ),
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.READ,
        )
    ),
):
    service = ProductMasterService(session)
    links = service.get_external_links(id, only_public=only_public, link_type=link_type)
    return [ProductMasterExternalLinkRead.model_validate(link) for link in links]


@router.patch(
    "/{id}/links/{link_id}",
    response_model=ProductMasterExternalLinkRead,
    summary="Actualizar metadatos de enlace externo",
    description=("Permite modificar URL, etiqueta, visibilidad pública o sort_order."),
)
def update_product_external_link(
    session: SessionDep,
    id: UUID,
    link_id: UUID,
    data: ProductMasterExternalLinkUpdate,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    link = service.update_external_link(id, link_id, data)
    return ProductMasterExternalLinkRead.model_validate(link)


@router.patch(
    "/{id}/links/{link_id}/primary",
    response_model=ProductMasterExternalLinkRead,
    summary="Fijar enlace como referencia externa principal",
    description=(
        "Designa este enlace como principal y actualiza la referencia de la ficha."
    ),
)
def set_primary_product_external_link(
    session: SessionDep,
    id: UUID,
    link_id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    link = service.set_primary_external_link(id, link_id)
    return ProductMasterExternalLinkRead.model_validate(link)


@router.put(
    "/{id}/links/reorder",
    response_model=list[ProductMasterExternalLinkRead],
    summary="Reordenar la secuencia de enlaces externos (drag & drop)",
    description="Actualiza el sort_order de los enlaces según el orden indicado.",
)
def reorder_product_external_links(
    session: SessionDep,
    id: UUID,
    items: list[ProductMasterExternalLinkReorderItem],
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    links = service.reorder_external_links(id, items)
    return [ProductMasterExternalLinkRead.model_validate(link) for link in links]


@router.delete(
    "/{id}/links/{link_id}",
    summary="Eliminar enlace externo de la ficha maestra",
    description=(
        "Elimina el enlace. Si el enlace eliminado era el principal, reasigna "
        "automáticamente el siguiente enlace disponible como principal."
    ),
)
def delete_product_external_link(
    session: SessionDep,
    id: UUID,
    link_id: UUID,
    _: UserModulePermission = Depends(
        PermissionChecker(
            module_slug=CommerceModuleSlug.GENERAL,
            required_permission=PermissionAction.UPDATE,
        )
    ),
):
    service = ProductMasterService(session)
    service.delete_external_link(id, link_id)
    return {"message": "Enlace externo eliminado exitosamente"}
