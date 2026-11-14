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
        default=None,
        index=True,
        unique=True,
        description="Número de catálogo limpio de la ficha maestra (1, 2, 53, 54...)",
    )
    code: str | None = Field(
        default=None,
        index=True,
        max_length=50,
        description="Código de barras o SKU comercial opcional ('0998399343434')",
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
    images: List["ProductMasterImage"] = Relationship(
        back_populates="product_master",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProductMasterImage.sort_order",
        },
    )
    external_links: List["ProductMasterExternalLink"] = Relationship(
        back_populates="product_master",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProductMasterExternalLink.sort_order",
        },
    )

    @property
    def marketplace_url(self) -> str | None:
        """URL de la publicación principal de marketplace."""
        if not self.external_links:
            return None
        for lnk in self.external_links:
            is_mkt = getattr(lnk, "link_type", "REFERENCE") == "MARKETPLACE"
            if is_mkt and lnk.is_primary:
                return lnk.url
        for lnk in self.external_links:
            if getattr(lnk, "link_type", "REFERENCE") == "MARKETPLACE":
                return lnk.url
        return None

    @property
    def external_info_url(self) -> str | None:
        """URL de referencia técnica externa principal (propiedad retrocompatible)."""
        if not self.external_links:
            return None
        for lnk in self.external_links:
            if getattr(lnk, "link_type", "REFERENCE") == "REFERENCE" and lnk.is_primary:
                return lnk.url
        for lnk in self.external_links:
            if getattr(lnk, "link_type", "REFERENCE") == "REFERENCE":
                return lnk.url
        return None


class ProductMasterImage(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_product_master_image"

    product_master_id: UUID = Field(
        foreign_key="commerce_product_master.id",
        index=True,
        description="Ficha maestra a la que pertenece esta fotografía o creativo",
    )
    product_id: UUID | None = Field(
        default=None,
        foreign_key="commerce_product.id",
        index=True,
        description=(
            "Producto físico específico si es fotografía de estado real / unboxing"
        ),
    )
    url: str = Field(
        max_length=500,
        description="URL pública optimizada de Cloudinary (HTTPS WebP)",
    )
    public_id: str = Field(
        max_length=255,
        index=True,
        description="ID del recurso en Cloudinary para gestión y eliminación",
    )
    image_type: str = Field(
        default="CATALOG",
        max_length=30,
        index=True,
        description=(
            "Categoría comercial: CATALOG (web), REAL (almacén), MARKETING (banners)"
        ),
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Título o texto alternativo de la imagen",
    )
    original_filename: str | None = Field(
        default=None,
        max_length=255,
        description="Nombre original del archivo al subirse",
    )
    file_size_bytes: int | None = Field(
        default=None, description="Peso del archivo en bytes"
    )
    width: int | None = Field(default=None, description="Ancho en píxeles")
    height: int | None = Field(default=None, description="Alto en píxeles")
    format: str | None = Field(
        default=None, max_length=10, description="Formato (webp, png, jpg, etc.)"
    )
    is_cover: bool = Field(
        default=False,
        index=True,
        description="¿Es la fotografía de portada oficial del producto?",
    )
    sort_order: int = Field(
        default=0,
        index=True,
        description="Orden de aparición en carruseles y galerías (1, 2, 3...)",
    )

    # Relationships
    product_master: Optional["ProductMaster"] = Relationship(back_populates="images")
    product: Optional["Product"] = Relationship()


# Alias de retrocompatibilidad
ProductImage = ProductMasterImage


class ProductMasterExternalLink(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_product_master_external_link"

    product_master_id: UUID = Field(
        foreign_key="commerce_product_master.id",
        index=True,
        description="Ficha Maestra a la que pertenece este enlace externo",
    )
    url: str = Field(
        max_length=1000,
        description="URL completa del producto en el portal externo de referencia",
    )
    portal: str = Field(
        default="OTHER",
        max_length=50,
        index=True,
        description=(
            "Identificador del portal: AMAZON, EBAY, ALIBABA, ALIEXPRESS, "
            "WALMART, MERCADOLIBRE, FACEBOOK, INSTAGRAM, TIKTOK, YOUTUBE, OTHER"
        ),
    )
    link_type: str = Field(
        default="REFERENCE",
        max_length=20,
        index=True,
        description=(
            "Tipo de enlace: 'REFERENCE' (info técnica/proveedor) o "
            "'MARKETPLACE' (publicación propia en tiendas/redes)"
        ),
    )
    label: str | None = Field(
        default=None,
        max_length=150,
        description="Etiqueta visible: ej. 'Amazon UK', 'eBay', 'Ficha Oficial'",
    )
    is_primary: bool = Field(
        default=False,
        index=True,
        description="¿Es el enlace principal de referencia técnica?",
    )
    is_public: bool = Field(
        default=True,
        index=True,
        description="¿Visible para el cliente en el catálogo público / PWA?",
    )
    sort_order: int = Field(
        default=0,
        index=True,
        description="Orden de visualización (1, 2, 3...)",
    )

    # Relationships
    product_master: Optional["ProductMaster"] = Relationship(
        back_populates="external_links"
    )


# Alias de retrocompatibilidad
ProductExternalLink = ProductMasterExternalLink
