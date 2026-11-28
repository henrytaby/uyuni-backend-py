from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import false
from sqlmodel import Session, col, or_, select

from app.core.filters import FilterOp, FilterSpec, accent_insensitive_ilike
from app.core.repository import BaseRepository
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.product_masters.models import ProductMaster


def build_product_master_search_filters(search: str) -> list[Any]:
    """Construye las cláusulas de búsqueda global sobre ProductMaster."""
    cleaned = search.strip()
    if not cleaned:
        return []

    search_filters: list[Any] = [
        accent_insensitive_ilike(col(ProductMaster.code), cleaned),
        accent_insensitive_ilike(col(ProductMaster.name), cleaned),
        accent_insensitive_ilike(col(ProductMaster.brand), cleaned),
        accent_insensitive_ilike(col(ProductMaster.model), cleaned),
        accent_insensitive_ilike(col(ProductMaster.description), cleaned),
        accent_insensitive_ilike(col(ProductMaster.features), cleaned),
    ]
    num = parse_search_int(cleaned, prefixes=("#", "NOV-"))
    if num is not None:
        search_filters.append(col(ProductMaster.item_number) == num)

    return search_filters


def build_product_master_id_subquery(search: str) -> Any:
    """Subconsulta de IDs de ProductMaster que coinciden con la búsqueda global."""
    search_filters = build_product_master_search_filters(search)
    if not search_filters:
        return select(col(ProductMaster.id)).where(false())
    return select(col(ProductMaster.id)).where(or_(*search_filters))


class ProductMasterRepository(BaseRepository[ProductMaster]):
    searchable_fields = ["code", "name", "brand", "model", "description", "features"]
    filter_fields = {
        "category_id": FilterOp.EQ,
        "category_ids": FilterSpec("category_id", FilterOp.IN),
        "storage_location_id": FilterOp.EQ,
        "storage_location_ids": FilterSpec("storage_location_id", FilterOp.IN),
        "is_active": FilterOp.EQ,
        "has_video": FilterOp.EQ,
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

        search_filters = build_product_master_search_filters(search)
        if not search_filters:
            return statement

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
