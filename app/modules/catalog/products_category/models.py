from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product


class ProductCategory(BaseModel, AuditMixin, table=True):
    """
    ProductCategory model that represents a product category in the database.
    """

    __tablename__ = "product_categories"

    name: str = Field(default=None, description="The name of the product category")
    description: Optional[str] = Field(
        default=None, description="The description of the product category"
    )

    products: List["Product"] = Relationship(back_populates="category")
