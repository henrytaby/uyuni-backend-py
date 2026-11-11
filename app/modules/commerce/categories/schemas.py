from uuid import UUID

from pydantic import BaseModel


class CategoryBase(BaseModel):
    code: str
    name: str
    icon: str | None = None
    description: str | None = None
    typical_products: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    typical_products: str | None = None


class CategoryRead(CategoryBase):
    id: UUID
