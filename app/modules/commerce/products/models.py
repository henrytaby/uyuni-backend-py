from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.batches.models import Batch
    from app.modules.commerce.product_masters.models import ProductMaster
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

    # 5. Costo unitario real de esta caja / lote
    cost_price: float | None = Field(
        default=None,
        description="Costo unitario asignado a esta unidad física según el lote",
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
        description="AVAILABLE, RESERVED, SOLD_OUT, SCRAPPED",
    )
    physical_condition: str = Field(
        default="OPERATIONAL",
        max_length=50,
        description="OPERATIONAL, DAMAGED_SCRAP, FOR_PARTS, INCOMPLETE, REPAIRED",
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

    # Propiedades delegadas de conveniencia hacia la Ficha Maestra
    @property
    def name(self) -> str:
        return self.master_product.name if self.master_product else ""

    @property
    def official_price(self) -> float:
        return self.master_product.official_price if self.master_product else 0.0

    @property
    def minimum_price(self) -> float:
        return self.master_product.minimum_price if self.master_product else 0.0

    @property
    def published_price(self) -> float:
        return self.master_product.published_price if self.master_product else 0.0

    @property
    def category_id(self) -> UUID | None:
        return self.master_product.category_id if self.master_product else None

    @property
    def live_basket_id(self) -> UUID | None:
        return self.master_product.live_basket_id if self.master_product else None

    @property
    def batch_name(self) -> str | None:
        return self.batch.name if self.batch else None
