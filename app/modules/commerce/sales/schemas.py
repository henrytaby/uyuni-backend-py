from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.commerce.constants import (
    SaleDeliveryModality,
    SaleDeliveryPaidBy,
    SaleDeliveryStatus,
    SalePaymentMethod,
    SalePaymentStatus,
)


class SaleItemBase(BaseModel):
    product_id: UUID
    quantity: int = 1
    unit_price: float


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, gt=0)
    unit_price: float = Field(ge=0)


class SaleItemRead(SaleItemBase):
    id: UUID
    sale_id: UUID
    item_number: int | None = None
    code: str | None = None
    product_name: str = ""
    variant_name: str | None = None
    unit_cost: float
    total_price: float
    net_margin: float


class SaleBase(BaseModel):
    customer_name: str = "Cliente Casual"
    customer_phone: str | None = None
    channel_id: UUID | None = None
    channel: str = "MARKETPLACE"
    payment_method: str = "QR"
    payment_status: str = "COLLECTED"
    delivery_modality: str = "FREE_MEETING_POINT"
    delivery_address: str | None = None
    delivery_cost: float = 0.0
    delivery_cost_paid_by: str = "FREE"
    delivery_status: str = "DELIVERED"
    amount_tendered: float | None = None
    change_given: float | None = None
    total_collected: float = 0.0
    currency: str = "BOB"
    observations: str | None = None


class SaleCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sale_number: int | None = None
    sheet_sale_id: int | None = None
    sale_date: datetime | None = None
    customer_name: str = "Cliente Casual"
    customer_phone: str | None = None
    channel_id: UUID | None = None
    channel: str = "MARKETPLACE"
    payment_method: SalePaymentMethod = SalePaymentMethod.QR
    payment_status: SalePaymentStatus = SalePaymentStatus.COLLECTED
    delivery_modality: SaleDeliveryModality = SaleDeliveryModality.FREE_MEETING_POINT
    delivery_address: str | None = None
    delivery_cost: float = Field(default=0.0, ge=0)
    delivery_cost_paid_by: SaleDeliveryPaidBy = SaleDeliveryPaidBy.FREE
    delivery_status: SaleDeliveryStatus = SaleDeliveryStatus.DELIVERED
    amount_tendered: float | None = Field(default=None, ge=0)
    change_given: float | None = Field(default=None, ge=0)
    total_collected: float | None = Field(default=None, ge=0)
    currency: str = "BOB"
    observations: str | None = None
    allow_below_minimum: bool = False
    items: list[SaleItemCreate]


class SaleUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sale_date: datetime | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    channel_id: UUID | None = None
    channel: str | None = None
    payment_method: SalePaymentMethod | None = None
    payment_status: SalePaymentStatus | None = None
    delivery_modality: SaleDeliveryModality | None = None
    delivery_address: str | None = None
    delivery_cost: float | None = Field(default=None, ge=0)
    delivery_cost_paid_by: SaleDeliveryPaidBy | None = None
    delivery_status: SaleDeliveryStatus | None = None
    amount_tendered: float | None = Field(default=None, ge=0)
    change_given: float | None = Field(default=None, ge=0)
    currency: str | None = None
    observations: str | None = None
    allow_below_minimum: bool = False
    items: list[SaleItemCreate] | None = None


class SaleRead(SaleBase):
    id: UUID
    sale_number: int
    channel_name: str = ""
    sheet_sale_id: int | None = None
    sale_date: datetime
    total_cost: float
    net_profit: float
    items: list[SaleItemRead] = []


class AvailableProductForSale(BaseModel):
    """Producto físico disponible para agregar a ventas (Catálogo POS)."""

    id: UUID
    master_product_id: UUID
    item_number: int | None = None
    code: str | None = None
    name: str
    display_name: str = ""
    variant_name: str | None = None
    batch_code: str | None = None
    batch_name: str | None = None
    available_quantity: int
    published_price: float
    minimum_price: float
    official_price: float
    discount_margin: float
    currency: str = "BOB"
    image_url: str | None = None


