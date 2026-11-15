from typing import Any
from uuid import UUID

from pydantic import BaseModel, model_validator


class ProductBase(BaseModel):
    master_product_id: UUID
    batch_id: UUID | None = None
    sheet_row_id: int | None = None
    variant_name: str | None = None
    cost_price: float | None = None
    published_price: float | None = None
    minimum_price: float | None = None
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
    published_price: float | None = None
    minimum_price: float | None = None
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
    item_number: int | None = None
    master_code: str | None = None
    image_url: str | None = None
    category_name: str | None = None
    batch_code: str | None = None
    batch_name: str | None = None
    currency: str = "BOB"
    official_price: float = 0.0
    minimum_price: float = 0.0
    published_price: float = 0.0
    estimated_margin: float | None = None
    discount_margin: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def fallback_prices(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            pub = getattr(data, "published_price", None)
            min_p = getattr(data, "minimum_price", None)
            master = getattr(data, "master_product", None)
            if (pub is None or min_p is None) and master:
                d = {k: getattr(data, k) for k in dir(data) if not k.startswith("_")}
                if pub is None:
                    d["published_price"] = (
                        getattr(master, "published_price", 0.0) or 0.0
                    )
                if min_p is None:
                    d["minimum_price"] = getattr(master, "minimum_price", 0.0) or 0.0
                return d
        return data
