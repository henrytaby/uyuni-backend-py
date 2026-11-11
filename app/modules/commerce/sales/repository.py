from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.commerce.sales.models import Sale, SaleItem


class SaleRepository(BaseRepository[Sale]):
    searchable_fields = [
        "sale_number",
        "customer_name",
        "channel",
        "payment_method",
        "payment_status",
        "delivery_status",
    ]

    def __init__(self, session: Session):
        super().__init__(session, Sale)


class SaleItemRepository(BaseRepository[SaleItem]):
    def __init__(self, session: Session):
        super().__init__(session, SaleItem)
