from typing import Any

from sqlmodel import Session, col, or_

from app.core.filters import FilterOp, FilterSpec
from app.core.repository import BaseRepository
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product


class ProductRepository(BaseRepository[Product]):
    searchable_fields = [
        "variant_name",
        "status",
        "physical_condition",
        "defect_detail",
    ]
    filter_fields = {
        "batch_id": FilterOp.EQ,
        "batch_ids": FilterSpec("batch_id", FilterOp.IN),
        "without_batch": FilterSpec("batch_id", FilterOp.IS_NULL),
        "master_product_id": FilterOp.EQ,
        "status": FilterOp.EQ,
        "statuses": FilterSpec("status", FilterOp.IN),
        "physical_condition": FilterOp.EQ,
        "physical_conditions": FilterSpec("physical_condition", FilterOp.IN),
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

        search_term = f"%{search}%"
        statement = statement.join(ProductMaster, isouter=True)
        search_filters: list[Any] = [
            col(ProductMaster.name).ilike(search_term),
            col(ProductMaster.code).ilike(search_term),
            col(ProductMaster.brand).ilike(search_term),
            col(ProductMaster.model).ilike(search_term),
            col(Product.variant_name).ilike(search_term),
            col(Product.status).ilike(search_term),
            col(Product.physical_condition).ilike(search_term),
            col(Product.defect_detail).ilike(search_term),
        ]
        num = parse_search_int(search, prefixes=("#", "NOV-"))
        if num is not None:
            search_filters.append(col(ProductMaster.item_number) == num)
            search_filters.append(col(Product.sheet_row_id) == num)

        return statement.where(or_(*search_filters))
