from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product


class ProductBrand(BaseModel, AuditMixin, table=True):
    __tablename__ = "product_brands"

    name: str = Field(default=None)
    description: str | None = Field(default=None)

    products: List["Product"] = Relationship(back_populates="brand")
