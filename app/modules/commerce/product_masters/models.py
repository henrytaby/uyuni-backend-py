from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.categories.models import Category
    from app.modules.commerce.live_baskets.models import LiveBasket
    from app.modules.commerce.products.models import Product


class ProductMaster(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_product_master"

    # Identificación numérica limpia y código de búsqueda
    item_number: int = Field(
        index=True,
        unique=True,
        description="Número de catálogo limpio de la ficha maestra (1, 2, 53, 54...)",
    )
    code: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Código de búsqueda normalizado ('53', 'NOV-053')",
    )
    name: str = Field(
        max_length=255, index=True, description="Nombre oficial de la ficha maestra"
    )
    description: str | None = Field(default=None, max_length=2000)

    category_id: UUID | None = Field(
        default=None, foreign_key="commerce_category.id", index=True
    )
    live_basket_id: UUID | None = Field(
        default=None, foreign_key="commerce_live_basket.id", index=True
    )
    brand: str | None = Field(default=None, max_length=150)
    model: str | None = Field(default=None, max_length=150)

    # Precios de referencia de catálogo
    official_price: float = Field(default=0.0, description="Precio de venta oficial")
    minimum_price: float = Field(
        default=0.0, description="Piso mínimo de regateo protegido"
    )
    published_price: float = Field(
        default=0.0, description="Precio publicado de referencia"
    )
    currency: str = Field(
        default="BOB", max_length=3, description="Código ISO 4217 (BOB, USD, etc.)"
    )

    # Multimedia, Marketing y Publicación en Redes
    cover_image_url: str | None = Field(default=None, max_length=500)
    marketplace_url: str | None = Field(default=None, max_length=500)
    external_info_url: str | None = Field(default=None, max_length=500)
    features: str | None = Field(default=None, max_length=2000)
    marketing_details: str | None = Field(default=None, max_length=2000)
    is_reviewed: bool = Field(
        default=False, description="¿Ficha comercial revisada y aprobada?"
    )
    is_fb_verified: bool = Field(
        default=False, description="¿Creativos listos para Facebook?"
    )
    has_video: bool = Field(default=False, description="¿Tiene video grabado?")
    is_published_marketplace: bool = Field(
        default=False, description="¿Activo en FB Marketplace?"
    )
    is_whatsapp_published: bool = Field(
        default=False, description="¿Publicado en grupos de WhatsApp?"
    )
    is_active: bool = Field(default=True, index=True)

    # Relationships
    category: Optional["Category"] = Relationship(back_populates="product_masters")
    live_basket: Optional["LiveBasket"] = Relationship(back_populates="product_masters")
    inventory_items: List["Product"] = Relationship(back_populates="master_product")
