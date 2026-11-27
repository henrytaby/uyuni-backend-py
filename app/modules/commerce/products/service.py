from typing import Any, Mapping, Sequence
from uuid import UUID

from sqlalchemy import and_, case, func
from sqlmodel import Session, col, select

from app.core.exceptions import NotFoundException
from app.core.filters import BaseFilterParams
from app.modules.commerce.product_masters.models import (
    ProductMaster,
    ProductMasterImage,
)
from app.modules.commerce.products.models import Product
from app.modules.commerce.products.repository import ProductRepository


class ProductService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProductRepository(session)

    def create(self, data: Product) -> Product:
        # Heredar precios de la Ficha Maestra si no se enviaron
        if data.master_product_id:
            master = self.session.get(ProductMaster, data.master_product_id)
            if master:
                if data.published_price is None or data.published_price <= 0:
                    data.published_price = master.published_price
                if data.minimum_price is None or data.minimum_price <= 0:
                    data.minimum_price = master.minimum_price

        # Calculate available quantity automatically
        data.available_quantity = max(
            0, data.initial_quantity - data.sold_quantity - data.merma_quantity
        )
        if data.merma_quantity >= data.initial_quantity and data.initial_quantity > 0:
            data.status = "SCRAPPED"
            if not data.physical_condition or data.physical_condition == "OPERATIONAL":
                data.physical_condition = "DAMAGED_SCRAP"
        elif data.available_quantity <= 0 and data.sold_quantity > 0:
            data.status = "SOLD_OUT"
        else:
            data.status = "AVAILABLE"

        created = self.repository.create(data)
        if created.batch_id:
            from app.modules.commerce.batches.service import BatchService

            BatchService(self.session).recalculate_from_products(created.batch_id)

        return created

    @staticmethod
    def _resolve_filters_and_extra(
        filters: BaseFilterParams | Mapping[str, Any] | None,
        batch_id: UUID | None,
        master_product_id: UUID | None,
        status: str | None,
    ) -> tuple[dict[str, Any], list[Any] | None]:
        merged: dict[str, Any] = (
            filters.to_filter_dict()
            if isinstance(filters, BaseFilterParams)
            else dict(filters or {})
        )
        if batch_id is not None:
            merged.setdefault("batch_id", batch_id)
        if master_product_id is not None:
            merged.setdefault("master_product_id", master_product_id)
        if status is not None:
            merged.setdefault("status", status)

        extra_filters: list[Any] = []
        category_id = merged.get("category_id")
        if category_id is not None:
            extra_filters.append(
                col(Product.master_product_id).in_(
                    select(col(ProductMaster.id)).where(
                        col(ProductMaster.category_id) == category_id
                    )
                )
            )

        min_price = merged.get("min_price")
        max_price = merged.get("max_price")
        if min_price is not None or max_price is not None:
            master_pub_sq = (
                select(col(ProductMaster.published_price))
                .where(col(ProductMaster.id) == col(Product.master_product_id))
                .scalar_subquery()
            )
            eff_price_expr: Any = case(
                (
                    and_(
                        col(Product.published_price).is_not(None),
                        col(Product.published_price) > 0,
                    ),
                    col(Product.published_price),
                ),
                else_=func.coalesce(master_pub_sq, 0.0),
            )
            if min_price is not None:
                extra_filters.append(eff_price_expr >= min_price)
            if max_price is not None:
                extra_filters.append(eff_price_expr <= max_price)

        return merged, (extra_filters or None)

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
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> Sequence[Product]:
        resolved_filters, extra_filters = self._resolve_filters_and_extra(
            filters, batch_id, master_product_id, status
        )

        return self.repository.get_all(
            offset,
            limit,
            sort_by,
            sort_order,
            search,
            extra_filters=extra_filters,
            filters=resolved_filters,
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

        # Proteger campos derivados contra manipulaciones manuales en payload
        data.pop("sold_quantity", None)
        data.pop("available_quantity", None)
        data.pop("status", None)

        # Si el lote asociado es de prorrateo (ej. Amazon WEIGHTED_RETAIL),
        # cost_price es derivado del lote, no editable a mano
        if product.batch and product.batch.costing_method in (
            "WEIGHTED_RETAIL",
            "FLAT_AVERAGE",
        ):
            data.pop("cost_price", None)

        for key, value in data.items():
            setattr(product, key, value)

        # Recalculate available stock and status
        product.available_quantity = max(
            0,
            product.initial_quantity - product.sold_quantity - product.merma_quantity,
        )
        if (
            product.merma_quantity >= product.initial_quantity
            and product.initial_quantity > 0
        ):
            product.status = "SCRAPPED"
            if (
                not product.physical_condition
                or product.physical_condition == "OPERATIONAL"
            ):
                product.physical_condition = "DAMAGED_SCRAP"
        elif product.available_quantity <= 0 and product.sold_quantity > 0:
            product.status = "SOLD_OUT"
        else:
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
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> int:
        resolved_filters, extra_filters = self._resolve_filters_and_extra(
            filters, batch_id, master_product_id, status
        )

        return self.repository.count(
            search=search, extra_filters=extra_filters, filters=resolved_filters
        )

    def get_images(self, product_id: UUID) -> list[ProductMasterImage]:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        stmt = (
            select(ProductMasterImage)
            .where(ProductMasterImage.product_id == product_id)
            .order_by(
                col(ProductMasterImage.sort_order).asc(),
                col(ProductMasterImage.created_at).asc(),
            )
        )
        return list(self.session.exec(stmt).all())

    def add_images(
        self,
        product_id: UUID,
        files_data: list[dict[str, Any]],
        is_public: bool = False,
    ) -> list[ProductMasterImage]:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        from app.modules.commerce.product_masters.service import (
            ProductMasterService,
        )

        master_service = ProductMasterService(self.session)
        return master_service.add_images(
            master_id=prod.master_product_id,
            files_data=files_data,
            image_type="REAL",
            is_cover=False,
            product_id=prod.id,
            is_public=is_public,
        )

    def update_image(
        self, product_id: UUID, image_id: UUID, data: Any
    ) -> ProductMasterImage:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        img = self.session.get(ProductMasterImage, image_id)
        if not img or img.product_id != product_id:
            raise NotFoundException(
                "Fotografía no encontrada para este producto físico"
            )

        from app.modules.commerce.product_masters.service import (
            ProductMasterService,
        )

        master_service = ProductMasterService(self.session)
        return master_service.update_image(prod.master_product_id, image_id, data)

    def delete_image(self, product_id: UUID, image_id: UUID) -> bool:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        img = self.session.get(ProductMasterImage, image_id)
        if not img or img.product_id != product_id:
            raise NotFoundException(
                "Fotografía no encontrada para este producto físico"
            )

        from app.modules.commerce.product_masters.service import (
            ProductMasterService,
        )

        master_service = ProductMasterService(self.session)
        return master_service.delete_image(prod.master_product_id, image_id)

    def delete_images_bulk(self, product_id: UUID, image_ids: list[UUID]) -> int:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        imgs = self.session.exec(
            select(ProductMasterImage).where(
                ProductMasterImage.product_id == product_id,
                col(ProductMasterImage.id).in_(image_ids),
            )
        ).all()

        from app.core.storage.cloudinary_service import cloudinary_service

        deleted_count = 0
        for img in imgs:
            if img.public_id:
                try:
                    cloudinary_service.delete_image(img.public_id)
                except Exception:
                    pass
            self.session.delete(img)
            deleted_count += 1

        self.session.commit()
        return deleted_count

    def reorder_images(
        self, product_id: UUID, items: Sequence[Any]
    ) -> list[ProductMasterImage]:
        prod = self.get_by_id(product_id)
        if not prod:
            raise NotFoundException(f"Producto físico {product_id} no encontrado")

        for item in items:
            img = self.session.get(ProductMasterImage, item.id)
            if img and img.product_id == product_id:
                img.sort_order = item.sort_order
                self.session.add(img)

        self.session.commit()
        return self.get_images(product_id)
