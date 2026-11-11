from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import DateTime, Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin
from app.util.datetime import get_current_time

if TYPE_CHECKING:
    from app.modules.commerce.channels.models import SalesChannel
    from app.modules.commerce.products.models import Product


class Sale(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_sale"

    sale_number: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Código de venta único (Ej: VTA-2026-0001)",
    )
    sheet_sale_id: int | None = Field(
        default=None, index=True, description="ID Venta de origen en Google Sheets"
    )
    sale_date: datetime = Field(
        default_factory=get_current_time,
        sa_type=DateTime(timezone=False),  # type: ignore
        index=True,
        description="Fecha y hora de la transacción",
    )

    # Datos del cliente
    customer_name: str = Field(default="Cliente Casual", max_length=150)
    customer_phone: str | None = Field(default=None, max_length=50)

    # Canal y Medio de Pago
    channel_id: UUID | None = Field(
        default=None, foreign_key="commerce_channel.id", index=True
    )
    channel: str = Field(
        default="Marketplace",
        max_length=50,
        description="Marketplace, WhatsApp, TikTok Live, Local",
    )
    payment_method: str = Field(
        default="QR", max_length=50, description="QR, CASH, TRANSFER, COURTESY"
    )
    payment_status: str = Field(
        default="COLLECTED",
        max_length=50,
        description="COLLECTED, PENDING, COURTESY, REFUNDED",
    )

    # Logística y entrega
    delivery_modality: str = Field(
        default="FREE_MEETING_POINT",
        max_length=100,
        description="FREE_MEETING_POINT, HOME_DELIVERY, TERMINAL_BUS, etc.",
    )
    delivery_address: str | None = Field(
        default=None, max_length=255, description="Dirección o punto de entrega"
    )
    delivery_cost: float = Field(default=0.0, description="Costo de transporte")
    delivery_cost_paid_by: str = Field(
        default="FREE",
        max_length=50,
        description="FREE, CUSTOMER, STORE",
    )
    delivery_status: str = Field(
        default="DELIVERED",
        max_length=50,
        description="DELIVERED, SHIPPED, PENDING",
    )

    # Consolidado Financiero
    total_collected: float = Field(
        default=0.0, description="Monto final efectivamente cobrado al cliente"
    )
    total_cost: float = Field(
        default=0.0,
        description="Costo agregado de los productos vendidos según el lote",
    )
    net_profit: float = Field(
        default=0.0, description="Ganancia neta real (total_collected - total_cost)"
    )
    currency: str = Field(
        default="BOB", max_length=3, description="Código ISO 4217 (BOB, USD, etc.)"
    )

    observations: str | None = Field(default=None, max_length=1000)

    # Relationships
    items: List["SaleItem"] = Relationship(back_populates="sale")
    sales_channel: Optional["SalesChannel"] = Relationship(back_populates="sales")


class SaleItem(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_sale_item"

    sale_id: UUID = Field(foreign_key="commerce_sale.id", index=True)
    product_id: UUID = Field(foreign_key="commerce_product.id", index=True)

    quantity: int = Field(default=1, description="Cantidad vendida")
    unit_price: float = Field(
        default=0.0, description="Precio unitario acordado en la venta"
    )
    unit_cost: float = Field(
        default=0.0, description="Costo unitario del producto al momento de la venta"
    )
    total_price: float = Field(
        default=0.0, description="Precio total acordado (unit_price * quantity)"
    )
    net_margin: float = Field(
        default=0.0,
        description="Margen neto del ítem (total_price - (unit_cost * quantity))",
    )

    # Relationships
    sale: Optional["Sale"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="sale_items")

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else ""
