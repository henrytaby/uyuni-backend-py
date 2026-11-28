from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.product_masters.models import ProductMaster


class StorageLocation(BaseModel, AuditMixin, table=True):
    """Ubicación física o contenedor de exhibición y picking para productos."""

    __tablename__ = "commerce_storage_location"

    code: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Código único de ubicación (Ej: C1, EST-A, VIT-1, DEP-01)",
    )
    name: str = Field(
        max_length=150,
        index=True,
        description="Nombre corto (Taller & Auto, Estante A, Vitrina Principal, etc.)",
    )
    label: str = Field(
        max_length=200,
        description=(
            "Etiqueta para Selectbox (Canasta 1 - Taller & Auto, Estante A, etc.)"
        ),
    )
    location_type: str = Field(
        default="OTHER",
        max_length=30,
        index=True,
        description=(
            "Tipo de ubicación: BASKET, SHELF, SHOWCASE, RACK, WAREHOUSE, OTHER"
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Criterio de asignación y referencia física para encontrar el producto"
        ),
    )
    is_active: bool = Field(
        default=True,
        index=True,
        description="¿Ubicación activa para asignar nuevos productos?",
    )

    # Relationships
    product_masters: List["ProductMaster"] = Relationship(
        back_populates="storage_location"
    )
