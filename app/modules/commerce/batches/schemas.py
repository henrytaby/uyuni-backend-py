from datetime import date
from uuid import UUID

from pydantic import BaseModel


class BatchBase(BaseModel):
    code: str
    name: str
    investment_round_id: UUID | None = None
    provider: str | None = None
    batch_type: str | None = None
    costing_method: str = "WEIGHTED_RETAIL"
    purchase_date: date | None = None
    purchase_price: float = 0.0
    freight_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "BOB"
    initial_items_count: int = 0
    merma_items_count: int = 0
    sellable_items_count: int = 0
    unit_cost: float = 0.0
    status: str = "active"
    financial_status: str = "EN_RECUPERACION"
    observations: str | None = None


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    investment_round_id: UUID | None = None
    provider: str | None = None
    batch_type: str | None = None
    costing_method: str | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    freight_cost: float | None = None
    total_cost: float | None = None
    currency: str | None = None
    initial_items_count: int | None = None
    merma_items_count: int | None = None
    sellable_items_count: int | None = None
    unit_cost: float | None = None
    status: str | None = None
    financial_status: str | None = None
    observations: str | None = None


class BatchRead(BatchBase):
    id: UUID
