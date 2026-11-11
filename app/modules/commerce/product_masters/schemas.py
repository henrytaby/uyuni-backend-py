from uuid import UUID

from pydantic import BaseModel


class ProductMasterBase(BaseModel):
    item_number: int
    code: str | None = None
    name: str
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
    pass


class ProductMasterUpdate(BaseModel):
    item_number: int | None = None
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
    cover_image_url: str | None = None
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
    code: str
    total_available_stock: int = 0
    total_sold_stock: int = 0
    total_merma_stock: int = 0
