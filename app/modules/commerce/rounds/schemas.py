from datetime import date
from uuid import UUID

from pydantic import BaseModel


class InvestmentRoundBase(BaseModel):
    code: str
    name: str
    disbursement_date: date | None = None
    capital_invested: float = 0.0
    currency: str = "BOB"
    status: str = "active"
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
