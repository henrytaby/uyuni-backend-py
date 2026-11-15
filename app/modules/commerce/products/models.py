from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.batches.models import Batch
    from app.modules.commerce.product_masters.models import (
        ProductMaster,
        ProductMasterImage,
    )
    from app.modules.commerce.sales.models import SaleItem


class Product(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_product"

    # 1. Relación obligatoria con el Catálogo Maestro
    master_product_id: UUID = Field(
        foreign_key="commerce_product_master.id",
        index=True,
        description="Ficha Maestra que define identidad, precios y marketing",
    )

    # 2. Relación con la Caja / Lote de Importación (Origen físico)
    batch_id: UUID | None = Field(
        default=None,
        foreign_key="commerce_batch.id",
        index=True,
        description="Lote/Caja del que proviene este inventario",
    )

    # 3. Variante física o de diseño específica de este lote
    variant_name: str | None = Field(
        default=None,
        max_length=100,
        description="Variante física o de diseño (ej: Luna vs Sistema Solar)",
    )

    # 4. Trazabilidad transitoria (Excel)
    sheet_row_id: int | None = Field(
        default=None,
        index=True,
        description="ID numérico de origen en la hoja de cálculo de liquidación",
    )

    # 5. Costo unitario y precios específicos de esta caja / lote
    cost_price: float | None = Field(
        default=None,
        description="Costo unitario asignado a esta unidad física según el lote",
    )
    published_price: float | None = Field(
        default=None,
        description="Precio de venta específico para este lote físico",
    )
    minimum_price: float | None = Field(
        default=None,
        description="Piso mínimo de regateo específico para este lote físico",
    )

    # 6. Cantidades y existencias físicas de este lote
    initial_quantity: int = Field(
        default=1, description="Cantidad recibida inicialmente"
    )
    sold_quantity: int = Field(default=0, description="Cantidad vendida")
    merma_quantity: int = Field(default=0, description="Cantidad dañada / merma")
    available_quantity: int = Field(
        default=1, description="Stock disponible actualmente"
    )

    # 7. Estado del producto e inspección física de la unidad
    status: str = Field(
        default="AVAILABLE",
        index=True,
        max_length=50,
        description="AVAILABLE, SOLD_OUT, SCRAPPED (gestionado automáticamente)",
    )
    physical_condition: str = Field(
        default="OPERATIONAL",
        max_length=50,
        description="OPERATIONAL, DAMAGED_SCRAP, FOR_PARTS, INCOMPLETE",
    )
    defect_detail: str | None = Field(
        default=None,
        max_length=500,
        description="Detalle de fallas, raspón, accesorios faltantes o reparaciones",
    )
    is_reviewed: bool = Field(
        default=False,
        description="¿Fue probado físicamente que enciende y funciona?",
    )

    # Relationships
    master_product: "ProductMaster" = Relationship(back_populates="inventory_items")
    batch: Optional["Batch"] = Relationship(back_populates="products")
    sale_items: List["SaleItem"] = Relationship(back_populates="product")
    images: List["ProductMasterImage"] = Relationship(
        back_populates="product",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProductMasterImage.sort_order",
        },
    )

    # Propiedades delegadas de conveniencia hacia la Ficha Maestra
    @property
    def name(self) -> str:
        return self.master_product.name if self.master_product else ""

    @property
    def item_number(self) -> int | None:
        return self.master_product.item_number if self.master_product else None

    @property
    def master_code(self) -> str | None:
        return self.master_product.code if self.master_product else None

    @property
    def image_url(self) -> str | None:
        if not self.master_product:
            return None
        if self.master_product.cover_image_url:
            return self.master_product.cover_image_url
        if self.master_product.images:
            for img in self.master_product.images:
                if img.is_cover:
                    return img.url
            return self.master_product.images[0].url
        return None

    @property
    def category_name(self) -> str | None:
        if self.master_product and self.master_product.category:
            return self.master_product.category.name
        return None

    @property
    def batch_code(self) -> str | None:
        return self.batch.code if self.batch else None

    @property
    def batch_name(self) -> str | None:
        return self.batch.name if self.batch else None

    @property
    def currency(self) -> str:
        if self.master_product and self.master_product.currency:
            return self.master_product.currency
        return "BOB"

    @property
    def official_price(self) -> float:
        return self.master_product.official_price if self.master_product else 0.0

    @property
    def effective_minimum_price(self) -> float:
        if self.minimum_price is not None and self.minimum_price > 0:
            return self.minimum_price
        return self.master_product.minimum_price if self.master_product else 0.0

    @property
    def effective_published_price(self) -> float:
        if self.published_price is not None and self.published_price > 0:
            return self.published_price
        return self.master_product.published_price if self.master_product else 0.0

    @property
    def estimated_margin(self) -> float | None:
        if self.cost_price is not None and self.cost_price > 0:
            pub = self.effective_published_price
            if pub > 0:
                return round(pub - self.cost_price, 2)
        return None

    @property
    def discount_margin(self) -> float:
        pub = self.effective_published_price
        min_p = self.effective_minimum_price
        return max(0.0, round(pub - min_p, 2))

    @property
    def category_id(self) -> UUID | None:
        return self.master_product.category_id if self.master_product else None

    @property
    def live_basket_id(self) -> UUID | None:
        return self.master_product.live_basket_id if self.master_product else None
