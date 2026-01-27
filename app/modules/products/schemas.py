import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ..catalog.products_brand.schemas import ProductBrandRead
from ..catalog.products_category.schemas import ProductCategoryRead


class ProductBase(BaseModel):
    title: str | None = Field(default=None)
    price: int = 0
    description: Optional[str] = None
    image: Optional[str] = None


# Modelo para crear una nueva tarea (hereda de TaskBase)
class ProductCreate(ProductBase):
    category_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    image: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None


class ProductRead(ProductBase):
    id: uuid.UUID = Field(description="The primary key")
    created_at: Optional[datetime] = Field(
        None, description="The timestamp when the data was created"
    )
    category: Optional[ProductCategoryRead] = None  # Relación con la categoría
    brand: Optional[ProductBrandRead] = None  # Relación con la categoría
    model_config = {"from_attributes": True}
