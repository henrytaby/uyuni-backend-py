from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, col, or_, select

from app.core.repository import BaseRepository
from app.modules.commerce.product_masters.models import ProductMaster


class ProductMasterRepository(BaseRepository[ProductMaster]):
    searchable_fields = ["code", "name", "brand", "model", "features"]

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
            col(ProductMaster.features).ilike(search_term),
        ]
        cleaned = (
            search.strip().replace("#", "").replace("NOV-", "").replace("nov-", "")
        )
        if cleaned.isdigit():
            search_filters.append(col(ProductMaster.item_number) == int(cleaned))

        return statement.where(or_(*search_filters))

    def get_by_item_number(self, item_number: int) -> ProductMaster | None:
        statement = select(ProductMaster).where(
            ProductMaster.item_number == item_number
        )
        return self.session.exec(statement).first()

    def get_by_code(self, code: str) -> ProductMaster | None:
        statement = select(ProductMaster).where(ProductMaster.code == code)
        return self.session.exec(statement).first()

    def get_all_by_category(self, category_id: UUID) -> Sequence[ProductMaster]:
        statement = select(ProductMaster).where(
            ProductMaster.category_id == category_id
        )
        return self.session.exec(statement).all()
