from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.commerce.rounds.models import InvestmentRound


class InvestmentRoundRepository(BaseRepository[InvestmentRound]):
    searchable_fields = ["code", "name", "status"]

    def __init__(self, session: Session):
        super().__init__(session, InvestmentRound)
