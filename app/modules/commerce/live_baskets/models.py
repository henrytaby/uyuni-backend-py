from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.product_masters.models import ProductMaster


class LiveBasket(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_live_basket"

    code: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Ej: C1, C2, C3, C4, C+1, FONDO, NONE",
    )
    name: str = Field(
        max_length=150,
        description="Nombre corto (Taller & Auto, Cables & Regletas, etc.)",
    )
    label: str = Field(
        max_length=200,
        description="Etiqueta para Selectbox (Canasta 1 - Taller & Auto)",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Criterio de asignación y ayuda al operador",
    )
    price_range: str | None = Field(
        default=None, max_length=100, description="Ej: Bs. 40 - 200"
    )
    target_audience: str | None = Field(
        default=None, max_length=255, description="Público objetivo del live"
    )

    # Relationships
    product_masters: List["ProductMaster"] = Relationship(back_populates="live_basket")
