from typing import Any

from sqlmodel import Session, col, or_

from app.core.filters import FilterOp, FilterSpec, accent_insensitive_ilike
from app.core.repository import BaseRepository
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.product_masters.repository import (
    build_product_master_id_subquery,
)
from app.modules.commerce.products.models import Product


class ProductRepository(BaseRepository[Product]):
    searchable_fields = [
        "variant_name",
        "status",
        "defect_detail",
    ]
    filter_fields = {
        "batch_id": FilterOp.EQ,
        "batch_ids": FilterSpec("batch_id", FilterOp.IN),
        "without_batch": FilterSpec("batch_id", FilterOp.IS_NULL),
        "master_product_id": FilterOp.EQ,
        "status": FilterOp.EQ,
        "statuses": FilterSpec("status", FilterOp.IN),
        "is_reviewed": FilterOp.EQ,
        "min_cost_price": FilterSpec("cost_price", FilterOp.GTE),
        "max_cost_price": FilterSpec("cost_price", FilterOp.LTE),
        "min_available_qty": FilterSpec("available_quantity", FilterOp.GTE),
        "max_available_qty": FilterSpec("available_quantity", FilterOp.LTE),
    }

    def __init__(self, session: Session):
        super().__init__(session, Product)

    def _apply_search(self, statement: Any, search: str | None = None) -> Any:
        if not search:
            return statement

        cleaned = search.strip()
        if not cleaned:
            return statement

        search_filters: list[Any] = [
            col(Product.master_product_id).in_(
                build_product_master_id_subquery(cleaned)
            ),
            accent_insensitive_ilike(col(Product.variant_name), cleaned),
            accent_insensitive_ilike(col(Product.status), cleaned),
            accent_insensitive_ilike(col(Product.defect_detail), cleaned),
        ]
        num = parse_search_int(cleaned, prefixes=("#", "NOV-"))
        if num is not None:
            search_filters.append(col(Product.sheet_row_id) == num)

        return statement.where(or_(*search_filters))
