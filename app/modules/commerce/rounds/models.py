from datetime import date
from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.batches.models import Batch


class InvestmentRound(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_investment_round"

    code: str = Field(
        index=True, unique=True, max_length=50, description="Ej: RONDA-01, RONDA-02"
    )
    name: str = Field(
        max_length=150,
        description="Ej: 1ra Compra (Piloto), 2da Compra (Combo Paralelo)",
    )
    disbursement_date: date | None = Field(default=None)
    capital_invested: float = Field(
        default=0.0, description="Capital total desembolsado"
    )
    currency: str = Field(
        default="BOB", max_length=3, description="Código ISO 4217 (BOB, USD, etc.)"
    )
    status: str = Field(
        default="active",
        max_length=50,
        description="active, break_even_reached, liquidated",
    )
    observations: str | None = Field(default=None, max_length=1000)

    # Relationships
    batches: List["Batch"] = Relationship(back_populates="investment_round")
