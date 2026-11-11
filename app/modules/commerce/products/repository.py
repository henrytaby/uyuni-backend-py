from typing import Any

from sqlmodel import Session, col, or_

from app.core.repository import BaseRepository
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product


class ProductRepository(BaseRepository[Product]):
    searchable_fields = [
        "variant_name",
        "status",
        "physical_condition",
        "defect_detail",
    ]

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
            col(Product.variant_name).ilike(search_term),
            col(Product.status).ilike(search_term),
            col(Product.physical_condition).ilike(search_term),
            col(Product.defect_detail).ilike(search_term),
        ]
        if search.strip().isdigit():
            num = int(search.strip())
            search_filters.append(col(ProductMaster.item_number) == num)
            search_filters.append(col(Product.sheet_row_id) == num)

        return statement.where(or_(*search_filters))
