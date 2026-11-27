from sqlmodel import Session

from app.core.filters import FilterOp, FilterSpec
from app.core.repository import BaseRepository
from app.modules.commerce.rounds.models import InvestmentRound


class InvestmentRoundRepository(BaseRepository[InvestmentRound]):
    searchable_fields = ["code", "name", "status"]
    filter_fields = {
        "status": FilterOp.EQ,
        "statuses": FilterSpec("status", FilterOp.IN),
        "disbursement_date_from": FilterSpec("disbursement_date", FilterOp.DATE_FROM),
        "disbursement_date_to": FilterSpec("disbursement_date", FilterOp.DATE_TO),
        "min_capital": FilterSpec("capital_invested", FilterOp.GTE),
        "max_capital": FilterSpec("capital_invested", FilterOp.LTE),
    }

    def __init__(self, session: Session):
        super().__init__(session, InvestmentRound)
