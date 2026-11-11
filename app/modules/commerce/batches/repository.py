from sqlmodel import Session

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

    def __init__(self, session: Session):
        super().__init__(session, Batch)
