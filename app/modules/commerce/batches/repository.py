from sqlmodel import Session

from app.core.filters import FilterOp, FilterSpec
from app.core.repository import BaseRepository
from app.modules.commerce.batches.models import Batch


class BatchRepository(BaseRepository[Batch]):
    searchable_fields = [
        "code",
        "name",
        "provider",
        "batch_type",
        "status",
        "financial_status",
    ]
    filter_fields = {
        "investment_round_id": FilterOp.EQ,
        "investment_round_ids": FilterSpec("investment_round_id", FilterOp.IN),
        "without_round": FilterSpec("investment_round_id", FilterOp.IS_NULL),
        "status": FilterOp.EQ,
        "statuses": FilterSpec("status", FilterOp.IN),
        "financial_status": FilterOp.EQ,
        "financial_statuses": FilterSpec("financial_status", FilterOp.IN),
        "costing_method": FilterOp.EQ,
        "purchase_date_from": FilterSpec("purchase_date", FilterOp.DATE_FROM),
        "purchase_date_to": FilterSpec("purchase_date", FilterOp.DATE_TO),
        "min_total_cost": FilterSpec("total_cost", FilterOp.GTE),
        "max_total_cost": FilterSpec("total_cost", FilterOp.LTE),
    }

    def __init__(self, session: Session):
        super().__init__(session, Batch)
