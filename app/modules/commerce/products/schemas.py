from uuid import UUID

from pydantic import BaseModel


class ProductBase(BaseModel):
    master_product_id: UUID
    batch_id: UUID | None = None
    sheet_row_id: int | None = None
    variant_name: str | None = None
    cost_price: float | None = None
    initial_quantity: int = 1
    sold_quantity: int = 0
    merma_quantity: int = 0
    available_quantity: int = 1
    status: str = "AVAILABLE"
    physical_condition: str = "OPERATIONAL"
    defect_detail: str | None = None
    is_reviewed: bool = False


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    master_product_id: UUID | None = None
    batch_id: UUID | None = None
    sheet_row_id: int | None = None
    variant_name: str | None = None
    cost_price: float | None = None
    initial_quantity: int | None = None
    sold_quantity: int | None = None
    merma_quantity: int | None = None
    available_quantity: int | None = None
    status: str | None = None
    physical_condition: str | None = None
    defect_detail: str | None = None
    is_reviewed: bool | None = None


class ProductRead(ProductBase):
    id: UUID
    name: str = ""
    official_price: float = 0.0
    minimum_price: float = 0.0
    published_price: float = 0.0
    batch_name: str | None = None
