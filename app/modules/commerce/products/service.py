from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, select

from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product
from app.modules.commerce.products.repository import ProductRepository


class ProductService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProductRepository(session)

    def create(self, data: Product) -> Product:
        # Calculate available quantity automatically
        data.available_quantity = (
            data.initial_quantity - data.sold_quantity - data.merma_quantity
        )
        if data.available_quantity <= 0 and data.sold_quantity > 0:
            data.status = "SOLD_OUT"
        elif data.available_quantity <= 0 and data.merma_quantity > 0:
            data.status = "SCRAPPED"
        elif data.status != "RESERVED":
            data.status = "AVAILABLE"

        created = self.repository.create(data)
        if created.batch_id:
            from app.modules.commerce.batches.service import BatchService

            BatchService(self.session).recalculate_from_products(created.batch_id)

        return created

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        batch_id: UUID | None = None,
        master_product_id: UUID | None = None,
        status: str | None = None,
    ) -> Sequence[Product]:
        extra_filters: list[Any] = []
        if batch_id:
            extra_filters.append(Product.batch_id == batch_id)
        if master_product_id:
            extra_filters.append(Product.master_product_id == master_product_id)
        if status:
            extra_filters.append(Product.status == status)

        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, extra_filters=extra_filters
        )

    def get_by_id(self, id: UUID) -> Product | None:
        return self.repository.get_by_id(id)

    def get_by_sku(self, sku: str) -> Product | None:
        stmt = (
            select(Product)
            .join(ProductMaster)
            .where(ProductMaster.code == sku)
            .limit(1)
        )
        return self.session.exec(stmt).first()

    def update(self, id: UUID, data: dict) -> Product | None:
        product = self.repository.get_by_id(id)
        if not product:
            return None

        old_batch_id = product.batch_id

        for key, value in data.items():
            setattr(product, key, value)

        # Recalculate available stock and status
        product.available_quantity = (
            product.initial_quantity - product.sold_quantity - product.merma_quantity
        )
        if product.available_quantity <= 0 and product.sold_quantity > 0:
            product.status = "SOLD_OUT"
        elif product.available_quantity <= 0 and product.merma_quantity > 0:
            product.status = "SCRAPPED"
        elif product.status != "RESERVED":
            product.status = "AVAILABLE"

        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)

        # Recalculate affected batches
        from app.modules.commerce.batches.service import BatchService

        batch_service = BatchService(self.session)
        if product.batch_id:
            batch_service.recalculate_from_products(product.batch_id)
        if old_batch_id and old_batch_id != product.batch_id:
            batch_service.recalculate_from_products(old_batch_id)

        return product

    def delete(self, id: UUID) -> bool:
        product = self.repository.get_by_id(id)
        if not product:
            return False
        batch_id = product.batch_id
        success = self.repository.delete(id)
        if success and batch_id:
            from app.modules.commerce.batches.service import BatchService

            BatchService(self.session).recalculate_from_products(batch_id)
        return success

    def count(
        self,
        search: str | None = None,
        batch_id: UUID | None = None,
        master_product_id: UUID | None = None,
        status: str | None = None,
    ) -> int:
        extra_filters: list[Any] = []
        if batch_id:
            extra_filters.append(Product.batch_id == batch_id)
        if master_product_id:
            extra_filters.append(Product.master_product_id == master_product_id)
        if status:
            extra_filters.append(Product.status == status)

        return self.repository.count(search=search, extra_filters=extra_filters)
