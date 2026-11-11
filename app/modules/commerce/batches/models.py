from datetime import date
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.products.models import Product
    from app.modules.commerce.rounds.models import InvestmentRound


class Batch(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_batch"

    code: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Ej: DIGITAL, ATAUD-01, AMAZON-NEXT",
    )
    name: str = Field(max_length=150, description="Nombre de la caja / lote")
    investment_round_id: UUID | None = Field(
        default=None, foreign_key="commerce_investment_round.id"
    )

    provider: str | None = Field(default=None, max_length=150)
    batch_type: str | None = Field(
        default=None,
        max_length=150,
        description="Liquidación Electrónicos, Ataúd Amazon, etc.",
    )
    purchase_date: date | None = Field(default=None)

    # Costos
    purchase_price: float = Field(
        default=0.0, description="Precio de compra de la caja"
    )
    freight_cost: float = Field(
        default=0.0, description="Costo de envío / flete a destino"
    )
    total_cost: float = Field(
        default=0.0, description="Costo total puesto almacén (compra + flete)"
    )
    currency: str = Field(
        default="BOB", max_length=3, description="Código ISO 4217 (BOB, USD, etc.)"
    )

    # Conteo de ítems y costo unitario
    initial_items_count: int = Field(
        default=0, description="Unidades totales registradas en la caja"
    )
    merma_items_count: int = Field(
        default=0, description="Unidades defectuosas / mermadas"
    )
    sellable_items_count: int = Field(
        default=0, description="Unidades vendibles (iniciales - merma)"
    )
    unit_cost: float = Field(
        default=0.0,
        description="Costo promedio por unidad vendible (total_cost / sellable_items)",
    )

    status: str = Field(
        default="active", max_length=50, description="active, liquidated, archived"
    )
    financial_status: str = Field(
        default="EN_RECUPERACION",
        max_length=50,
        description="EN_RECUPERACION, RECUPERADO",
    )
    observations: str | None = Field(default=None, max_length=1000)

    # Relationships
    investment_round: Optional["InvestmentRound"] = Relationship(
        back_populates="batches"
    )
    products: List["Product"] = Relationship(back_populates="batch")
