import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from ..catalog.products_brand.models import ProductBrand
    from ..catalog.products_category.models import ProductCategory


class Product(BaseModel, AuditMixin, table=True):
    """
    Product model that represents a product in the database.
    """

    __tablename__ = "products"
    title: str = Field(default=None)
    price: int = 0
    description: Optional[str] = Field(default=None)
    image: str = Field(default=None)

    category_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="product_categories.id"
    )
    category: Optional["ProductCategory"] = Relationship(back_populates="products")

    brand_id: Optional[uuid.UUID] = Field(default=None, foreign_key="product_brands.id")
    brand: Optional["ProductBrand"] = Relationship(back_populates="products")
