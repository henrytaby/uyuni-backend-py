from typing import Any

from sqlmodel import Session, col, or_

from app.core.filters import FilterOp, FilterSpec
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
    filter_fields = {
        "channel": FilterOp.EQ,
        "channels": FilterSpec("channel", FilterOp.IN),
        "channel_id": FilterOp.EQ,
        "payment_method": FilterOp.EQ,
        "payment_methods": FilterSpec("payment_method", FilterOp.IN),
        "payment_status": FilterOp.EQ,
        "payment_statuses": FilterSpec("payment_status", FilterOp.IN),
        "delivery_status": FilterOp.EQ,
        "delivery_modality": FilterOp.EQ,
        "delivery_modalities": FilterSpec("delivery_modality", FilterOp.IN),
        "sale_date_from": FilterSpec("sale_date", FilterOp.DATE_FROM),
        "sale_date_to": FilterSpec("sale_date", FilterOp.DATE_TO),
        "min_total": FilterSpec("total_collected", FilterOp.GTE),
        "max_total": FilterSpec("total_collected", FilterOp.LTE),
        "min_profit": FilterSpec("net_profit", FilterOp.GTE),
        "max_profit": FilterSpec("net_profit", FilterOp.LTE),
    }

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
