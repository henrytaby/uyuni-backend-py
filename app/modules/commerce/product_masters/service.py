from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import BadRequestException
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.repository import ProductMasterRepository
from app.modules.commerce.products.models import Product


class ProductMasterService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProductMasterRepository(session)

    def create(self, data: ProductMaster) -> ProductMaster:
        if not data.code:
            data.code = str(data.item_number)

        existing_num = self.repository.get_by_item_number(data.item_number)
        if existing_num:
            raise BadRequestException(
                f"Ya existe una ficha maestra con el número #{data.item_number} "
                f"({existing_num.name})"
            )

        existing_code = self.repository.get_by_code(data.code)
        if existing_code:
            raise BadRequestException(
                f"Ya existe una ficha maestra con el código '{data.code}' "
                f"({existing_code.name})"
            )

        return self.repository.create(data)

    def get_by_id(self, id: UUID) -> ProductMaster | None:
        return self.repository.get_by_id(id)

    def get_by_item_number(self, item_number: int) -> ProductMaster | None:
        return self.repository.get_by_item_number(item_number)

    def get_by_code(self, code: str) -> ProductMaster | None:
        return self.repository.get_by_code(code)

    def resolve_by_identifier(self, identifier: str | int) -> ProductMaster | None:
        if isinstance(identifier, int):
            return self.get_by_item_number(identifier)

        raw = str(identifier).strip()
        found = self.get_by_code(raw)
        if found:
            return found

        # Tratar de interpretar como número ("53", "053", "NOV-053", "#53")
        cleaned = raw.upper()
        if cleaned.startswith("NOV-"):
            cleaned = cleaned.replace("NOV-", "")
        elif cleaned.startswith("#"):
            cleaned = cleaned.replace("#", "")

        try:
            num = int(cleaned)
            return self.get_by_item_number(num)
        except ValueError:
            return None

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        category_id: UUID | None = None,
        live_basket_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> Sequence[ProductMaster]:
        filters: list[Any] = []
        if category_id:
            filters.append(ProductMaster.category_id == category_id)
        if live_basket_id:
            filters.append(ProductMaster.live_basket_id == live_basket_id)
        if is_active is not None:
            filters.append(ProductMaster.is_active == is_active)

        return self.repository.get_all(
            offset=offset,
            limit=limit,
            sort_by=sort_by or "item_number",
            sort_order=sort_order,
            search=search,
            extra_filters=filters or None,
        )

    def count(
        self,
        search: str | None = None,
        category_id: UUID | None = None,
        live_basket_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> int:
        filters: list[Any] = []
        if category_id:
            filters.append(ProductMaster.category_id == category_id)
        if live_basket_id:
            filters.append(ProductMaster.live_basket_id == live_basket_id)
        if is_active is not None:
            filters.append(ProductMaster.is_active == is_active)

        return self.repository.count(search=search, extra_filters=filters or None)

    def update(self, id: UUID, data: dict) -> ProductMaster | None:
        if "item_number" in data and data["item_number"] is not None:
            existing = self.repository.get_by_item_number(data["item_number"])
            if existing and existing.id != id:
                raise BadRequestException(
                    f"El número #{data['item_number']} ya está asignado "
                    "a otra ficha maestra"
                )

        if "code" in data and data["code"] is not None:
            existing_c = self.repository.get_by_code(data["code"])
            if existing_c and existing_c.id != id:
                raise BadRequestException(
                    f"El código '{data['code']}' ya está asignado a otra ficha maestra"
                )

        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def get_stock_summary(self, master_id: UUID) -> dict[str, int]:
        statement = select(
            func.coalesce(func.sum(Product.available_quantity), 0),
            func.coalesce(func.sum(Product.sold_quantity), 0),
            func.coalesce(func.sum(Product.merma_quantity), 0),
        ).where(Product.master_product_id == master_id)

        result = self.session.exec(statement).first()
        if result:
            avail, sold, merma = result
            return {
                "available": int(avail),
                "sold": int(sold),
                "merma": int(merma),
            }
        return {"available": 0, "sold": 0, "merma": 0}
