from typing import Any

from sqlmodel import Session, col, or_

from app.core.repository import BaseRepository
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.sales.models import Sale, SaleItem


class SaleRepository(BaseRepository[Sale]):
    searchable_fields = [
        "customer_name",
        "customer_phone",
        "channel",
        "payment_method",
        "payment_status",
        "delivery_status",
        "delivery_address",
        "observations",
    ]

    def __init__(self, session: Session):
        super().__init__(session, Sale)

    def _apply_search(self, statement: Any, search: str | None = None) -> Any:
        if not search:
            return statement

        search_term = f"%{search}%"
        search_filters: list[Any] = [
            col(Sale.customer_name).ilike(search_term),
            col(Sale.channel).ilike(search_term),
            col(Sale.payment_method).ilike(search_term),
            col(Sale.payment_status).ilike(search_term),
            col(Sale.delivery_status).ilike(search_term),
        ]
        if Sale.delivery_address is not None:
            search_filters.append(col(Sale.delivery_address).ilike(search_term))
        if Sale.observations is not None:
            search_filters.append(col(Sale.observations).ilike(search_term))

        num = parse_search_int(search, prefixes=("#", "VTA-"))
        if num is not None:
            search_filters.append(col(Sale.sale_number) == num)
            search_filters.append(col(Sale.sheet_sale_id) == num)

        return statement.where(or_(*search_filters))


class SaleItemRepository(BaseRepository[SaleItem]):
    def __init__(self, session: Session):
        super().__init__(session, SaleItem)

