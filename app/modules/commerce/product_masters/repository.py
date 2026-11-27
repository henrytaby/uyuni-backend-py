from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, col, or_, select

from app.core.filters import FilterOp, FilterSpec
from app.core.repository import BaseRepository
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.product_masters.models import ProductMaster


class ProductMasterRepository(BaseRepository[ProductMaster]):
    searchable_fields = ["code", "name", "brand", "model", "description", "features"]
    filter_fields = {
        "category_id": FilterOp.EQ,
        "category_ids": FilterSpec("category_id", FilterOp.IN),
        "live_basket_id": FilterOp.EQ,
        "live_basket_ids": FilterSpec("live_basket_id", FilterOp.IN),
        "is_active": FilterOp.EQ,
        "is_published_marketplace": FilterOp.EQ,
        "is_whatsapp_published": FilterOp.EQ,
        "min_price": FilterSpec("published_price", FilterOp.GTE),
        "max_price": FilterSpec("published_price", FilterOp.LTE),
    }

    def __init__(self, session: Session):
        super().__init__(session, ProductMaster)

    def _apply_search(self, statement: Any, search: str | None = None) -> Any:
        if not search:
            return statement

        search_term = f"%{search}%"
        search_filters: list[Any] = [
            col(ProductMaster.code).ilike(search_term),
            col(ProductMaster.name).ilike(search_term),
            col(ProductMaster.brand).ilike(search_term),
            col(ProductMaster.model).ilike(search_term),
            col(ProductMaster.description).ilike(search_term),
            col(ProductMaster.features).ilike(search_term),
        ]
        num = parse_search_int(search, prefixes=("#", "NOV-"))
        if num is not None:
            search_filters.append(col(ProductMaster.item_number) == num)

        return statement.where(or_(*search_filters))

    def get_by_item_number(self, item_number: int) -> ProductMaster | None:
        statement = select(ProductMaster).where(
            ProductMaster.item_number == item_number
        )
        return self.session.exec(statement).first()

    def get_by_code(self, code: str | None) -> ProductMaster | None:
        if not code:
            return None
        statement = select(ProductMaster).where(ProductMaster.code == code)
        return self.session.exec(statement).first()

    def get_all_by_category(self, category_id: UUID) -> Sequence[ProductMaster]:
        statement = select(ProductMaster).where(
            ProductMaster.category_id == category_id
        )
        return self.session.exec(statement).all()
