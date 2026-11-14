from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductMasterImageBase(BaseModel):
    url: str
    public_id: str
    image_type: str = "CATALOG"
    title: str | None = None
    original_filename: str | None = None
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    is_cover: bool = False
    sort_order: int = 0


class ProductMasterImageRead(ProductMasterImageBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_master_id: UUID
    product_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductMasterImageUpdate(BaseModel):
    title: str | None = None
    image_type: str | None = None
    is_cover: bool | None = None
    sort_order: int | None = None


class ProductMasterImageReorderItem(BaseModel):
    id: UUID
    sort_order: int


# Aliases de compatibilidad para imágenes de ficha maestra
ProductImageBase = ProductMasterImageBase
ProductImageRead = ProductMasterImageRead
ProductImageUpdate = ProductMasterImageUpdate
ProductImageReorderItem = ProductMasterImageReorderItem


class ProductMasterExternalLinkBase(BaseModel):
    url: str
    portal: str = "OTHER"
    link_type: str = "REFERENCE"
    label: str | None = None
    is_primary: bool = False
    is_public: bool = True
    sort_order: int = 0


class ProductMasterExternalLinkCreate(BaseModel):
    url: str
    link_type: str = "REFERENCE"
    label: str | None = None
    is_primary: bool = False
    is_public: bool = True


class ProductMasterExternalLinkRead(ProductMasterExternalLinkBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_master_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductMasterExternalLinkUpdate(BaseModel):
    url: str | None = None
    link_type: str | None = None
    label: str | None = None
    is_primary: bool | None = None
    is_public: bool | None = None
    sort_order: int | None = None


class ProductMasterExternalLinkReorderItem(BaseModel):
    id: UUID
    sort_order: int


# Aliases de compatibilidad
ProductExternalLinkBase = ProductMasterExternalLinkBase
ProductExternalLinkCreate = ProductMasterExternalLinkCreate
ProductExternalLinkRead = ProductMasterExternalLinkRead
ProductExternalLinkUpdate = ProductMasterExternalLinkUpdate
ProductExternalLinkReorderItem = ProductMasterExternalLinkReorderItem


class ProductMasterBase(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    live_basket_id: UUID | None = None
    brand: str | None = None
    model: str | None = None

    # Precios de referencia de catálogo
    official_price: float = 0.0
    minimum_price: float = 0.0
    published_price: float = 0.0
    currency: str = "BOB"

    # Multimedia, Marketing y Publicación
    cover_image_url: str | None = None
    marketplace_url: str | None = None
    external_info_url: str | None = None
    features: str | None = None
    marketing_details: str | None = None
    is_reviewed: bool = False
    is_fb_verified: bool = False
    has_video: bool = False
    is_published_marketplace: bool = False
    is_whatsapp_published: bool = False
    is_active: bool = True


class ProductMasterCreate(ProductMasterBase):
    # item_number es autogenerado exclusivamente por el backend vía secuencia atómica
    pass


class ProductMasterUpdate(BaseModel):
    # item_number y cover_image_url son de solo lectura y se descartan si se envían:
    # - item_number es inmutable y autogenerado por secuencia
    # - cover_image_url se sincroniza automáticamente desde la galería (/images)
    code: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    live_basket_id: UUID | None = None
    brand: str | None = None
    model: str | None = None
    official_price: float | None = None
    minimum_price: float | None = None
    published_price: float | None = None
    currency: str | None = None
    marketplace_url: str | None = None
    external_info_url: str | None = None
    features: str | None = None
    marketing_details: str | None = None
    is_reviewed: bool | None = None
    is_fb_verified: bool | None = None
    has_video: bool | None = None
    is_published_marketplace: bool | None = None
    is_whatsapp_published: bool | None = None
    is_active: bool | None = None


class ProductMasterRead(ProductMasterBase):
    id: UUID
    item_number: int
    code: str | None = None
    total_available_stock: int = 0
    total_sold_stock: int = 0
    total_merma_stock: int = 0
    images: list[ProductMasterImageRead] = []
    images_count: int = 0
    external_links: list[ProductMasterExternalLinkRead] = []
    external_links_count: int = 0
    reference_links: list[ProductMasterExternalLinkRead] = []
    reference_links_count: int = 0
    marketplace_links: list[ProductMasterExternalLinkRead] = []
    marketplace_links_count: int = 0


# =========================================================================
# Schemas para Extracción e Importación de Imágenes Externas
# =========================================================================
class ScrapedImageCandidate(BaseModel):
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt: str | None = None


class ScrapedImagesResponse(BaseModel):
    source_url: str
    platform: str
    images: list[ScrapedImageCandidate]
    warning: str | None = None


class ScrapeImagesRequest(BaseModel):
    url: str


class ImportExternalImagesRequest(BaseModel):
    image_urls: list[str]
    image_type: str = "CATALOG"
    set_first_as_cover: bool = True
