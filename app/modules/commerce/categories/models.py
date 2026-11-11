from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.product_masters.models import ProductMaster


class Category(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_category"

    code: str = Field(
        index=True, unique=True, max_length=50, description="Ej: CAT-01, CAT-02"
    )
    name: str = Field(
        max_length=150, index=True, description="Nombre oficial de la categoría"
    )
    icon: str | None = Field(
        default=None, max_length=10, description="Emoji o icono de la categoría"
    )
    description: str | None = Field(default=None, max_length=1000)
    typical_products: str | None = Field(
        default=None, max_length=1000, description="Ejemplos típicos de productos"
    )

    # Relationships
    product_masters: List["ProductMaster"] = Relationship(back_populates="category")
