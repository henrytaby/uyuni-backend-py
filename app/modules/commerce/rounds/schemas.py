from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.filters import (
    BaseFilterParams,
    ListQueryMixin,
    MultiStr,
    OptDate,
    OptFloat,
    OptStr,
)


class InvestmentRoundFilterParams(BaseFilterParams):
    """Filtros estándar para listado y conteo de rondas de inversión."""

    status: OptStr = None
    statuses: MultiStr = None
    disbursement_date_from: OptDate = None
    disbursement_date_to: OptDate = None
    min_capital: OptFloat = None
    max_capital: OptFloat = None


class InvestmentRoundListQuery(ListQueryMixin, InvestmentRoundFilterParams):
    """Query params completos para listado paginado de rondas."""


class InvestmentRoundBase(BaseModel):
    code: str | None = None
    name: str
    disbursement_date: date | None = None
    capital_invested: float = 0.0
    currency: str = "BOB"
    status: str = "ACTIVE"
    observations: str | None = None


class InvestmentRoundCreate(InvestmentRoundBase):
    pass


class InvestmentRoundUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    disbursement_date: date | None = None
    capital_invested: float | None = None
    currency: str | None = None
    status: str | None = None
    observations: str | None = None


class InvestmentRoundRead(InvestmentRoundBase):
    id: UUID


class InvestmentRoundMetricsRead(BaseModel):
    round_id: UUID
    code: str
    name: str
    status: str
    capital_invested: float
    capital_recovered: float
    net_profit: float
    break_even_progress_percent: float
    is_break_even: bool
    batches_count: int
    total_items: int
    available_items: int
    sold_items: int
    merma_items: int
