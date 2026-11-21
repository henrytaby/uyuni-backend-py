from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SaleItemBase(BaseModel):
    product_id: UUID
    quantity: int = 1
    unit_price: float


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemRead(SaleItemBase):
    id: UUID
    sale_id: UUID
    product_name: str = ""
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
    sale_number: int | None = None
    sheet_sale_id: int | None = None
    sale_date: datetime | None = None
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
    total_collected: float | None = None
    currency: str = "BOB"
    observations: str | None = None
    allow_below_minimum: bool = False
    items: list[SaleItemCreate]


class SaleUpdate(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    channel_id: UUID | None = None
    channel: str | None = None
    payment_method: str | None = None
    payment_status: str | None = None
    delivery_modality: str | None = None
    delivery_address: str | None = None
    delivery_cost: float | None = None
    delivery_cost_paid_by: str | None = None
    delivery_status: str | None = None
    amount_tendered: float | None = None
    change_given: float | None = None
    currency: str | None = None
    observations: str | None = None


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

