from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, col, or_, select

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.constants import parse_search_int
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product
from app.modules.commerce.sales.models import Sale, SaleItem
from app.modules.commerce.sales.repository import SaleItemRepository, SaleRepository
from app.modules.commerce.sales.schemas import (
    AvailableProductForSale,
    SaleCreate,
    SaleItemCreate,
)
from app.util.datetime import _tz_offset, get_current_time


class SaleService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = SaleRepository(session)
        self.item_repository = SaleItemRepository(session)

    def get_next_sale_number(self) -> int:
        """Obtiene el siguiente número secuencial vía secuencia PostgreSQL."""
        bind = self.session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            from sqlalchemy import text

            res = self.session.execute(
                text("SELECT nextval('commerce_sale_sale_number_seq')")
            ).scalar_one()
            return int(res)

        from sqlmodel import func, select

        max_num = self.session.exec(select(func.max(Sale.sale_number))).one() or 0
        return int(max_num) + 1

    @staticmethod
    def _to_naive_local(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(_tz_offset).replace(tzinfo=None)

    @staticmethod
    def _resolve_cash_handling(
        payment_method: str,
        total_collected: float,
        amount_tendered: float | None,
    ) -> tuple[float, float]:
        """Calcula autoritativamente amount_tendered y change_given en el backend."""
        total = round(total_collected, 2)
        if payment_method != "CASH" or amount_tendered is None:
            return total, 0.0

        tendered = round(amount_tendered, 2)
        change = round(tendered - total, 2) if tendered >= total else 0.0
        return tendered, change

    def _prepare_sale_items(
        self,
        items_data: list[SaleItemCreate],
        allow_below_minimum: bool,
    ) -> tuple[list[dict[str, Any]], float, float]:
        """Valida stock, mínimos y costos unitarios para una lista de ítems."""
        if not items_data:
            raise BadRequestException(
                detail="A sale must contain at least one product item"
            )

        prepared_items: list[dict[str, Any]] = []
        total_items_price = 0.0
        total_cost = 0.0
        requested_by_product: dict[UUID, int] = {}

        for item_data in items_data:
            product = self.session.get(Product, item_data.product_id)
            if not product:
                raise NotFoundException(
                    detail=f"Product with ID '{item_data.product_id}' not found"
                )

            cumulative_qty = (
                requested_by_product.get(product.id, 0) + item_data.quantity
            )
            if product.available_quantity < cumulative_qty:
                msg = (
                    f"Stock insuficiente para '{product.name}'. "
                    f"Disponible: {product.available_quantity}, "
                    f"Solicitado: {cumulative_qty}"
                )
                raise BadRequestException(detail=msg)
            requested_by_product[product.id] = cumulative_qty

            effective_min = product.effective_minimum_price
            if (
                effective_min > 0
                and item_data.unit_price < effective_min
                and not allow_below_minimum
            ):
                msg = (
                    f"Precio pactado ({item_data.unit_price}) menor al mínimo "
                    f"({effective_min}) para '{product.name}'. "
                    "Requiere autorización (allow_below_minimum=True)."
                )
                raise BadRequestException(detail=msg)

            unit_cost = 0.0
            if product.cost_price is not None:
                unit_cost = product.cost_price
            elif product.batch_id:
                batch = self.session.get(Batch, product.batch_id)
                if batch:
                    unit_cost = batch.unit_cost

            item_total_price = round(item_data.unit_price * item_data.quantity, 2)
            item_total_cost = round(unit_cost * item_data.quantity, 2)
            item_net_margin = round(item_total_price - item_total_cost, 2)

            total_items_price += item_total_price
            total_cost += item_total_cost

            prepared_items.append(
                {
                    "product": product,
                    "quantity": item_data.quantity,
                    "unit_price": item_data.unit_price,
                    "unit_cost": unit_cost,
                    "total_price": item_total_price,
                    "net_margin": item_net_margin,
                }
            )

        return prepared_items, total_items_price, total_cost

    @staticmethod
    def _recompute_product_stock(product: Product) -> None:
        """Recalcula available_quantity y status físico tras modificar sold_quantity."""
        product.available_quantity = max(
            0,
            product.initial_quantity - product.sold_quantity - product.merma_quantity,
        )
        if (
            product.merma_quantity >= product.initial_quantity
            and product.initial_quantity > 0
        ):
            product.status = "SCRAPPED"
        elif product.available_quantity <= 0 and product.sold_quantity > 0:
            product.status = "SOLD_OUT"
        else:
            product.status = "AVAILABLE"

    def _collect_batch_round_ids(
        self, product: Product, batch_ids: set[UUID], round_ids: set[UUID]
    ) -> None:
        if product.batch_id:
            batch_ids.add(product.batch_id)
            batch = self.session.get(Batch, product.batch_id)
            if batch and batch.investment_round_id:
                round_ids.add(batch.investment_round_id)

    def _restore_items_stock(
        self, sale_items: Sequence[SaleItem]
    ) -> tuple[set[UUID], set[UUID]]:
        """Devuelve al almacén las unidades vendidas de los ítems indicados."""
        batch_ids: set[UUID] = set()
        round_ids: set[UUID] = set()
        for item in sale_items:
            product = self.session.get(Product, item.product_id)
            if product:
                product.sold_quantity = max(0, product.sold_quantity - item.quantity)
                self._recompute_product_stock(product)
                self.session.add(product)
                self._collect_batch_round_ids(product, batch_ids, round_ids)
        return batch_ids, round_ids

    def _apply_prepared_items(
        self, sale_id: UUID, prepared_items: list[dict[str, Any]]
    ) -> tuple[set[UUID], set[UUID]]:
        """Persiste los SaleItem y descuenta el inventario atómicamente."""
        batch_ids: set[UUID] = set()
        round_ids: set[UUID] = set()
        for p_item in prepared_items:
            product: Product = p_item["product"]
            sale_item = SaleItem(
                sale_id=sale_id,
                product_id=product.id,
                quantity=p_item["quantity"],
                unit_price=p_item["unit_price"],
                unit_cost=p_item["unit_cost"],
                total_price=p_item["total_price"],
                net_margin=p_item["net_margin"],
            )
            self.session.add(sale_item)

            product.sold_quantity += p_item["quantity"]
            self._recompute_product_stock(product)
            self.session.add(product)
            self._collect_batch_round_ids(product, batch_ids, round_ids)
        return batch_ids, round_ids

    def _sync_affected_batches_and_rounds(
        self, batch_ids: set[UUID], round_ids: set[UUID]
    ) -> None:
        if batch_ids:
            from app.modules.commerce.batches.service import BatchService

            batch_service = BatchService(self.session)
            for b_id in batch_ids:
                batch_service.sync_financial_status(b_id)

        if round_ids:
            from app.modules.commerce.rounds.service import InvestmentRoundService

            round_service = InvestmentRoundService(self.session)
            for r_id in round_ids:
                round_service.recalculate_round(r_id)

    def create(self, data: SaleCreate) -> Sale:
        # 1. Validation & Pre-computation phase
        prepared_items, total_items_price, total_cost = self._prepare_sale_items(
            data.items, data.allow_below_minimum
        )

        # 2. Determine final financial totals
        final_collected = (
            data.total_collected
            if data.total_collected is not None
            else round(total_items_price, 2)
        )
        store_delivery = (
            data.delivery_cost if data.delivery_cost_paid_by == "STORE" else 0.0
        )
        net_profit = round(final_collected - total_cost - store_delivery, 2)

        # 3. Determine atomic sale_number
        sale_number = data.sale_number
        if sale_number is None or sale_number <= 0:
            sale_number = self.get_next_sale_number()

        # 4. Handle cash tendered and change given (siempre calculado en backend)
        amount_tendered, change_given = self._resolve_cash_handling(
            data.payment_method,
            final_collected,
            data.amount_tendered,
        )

        sale_date = (
            self._to_naive_local(data.sale_date)
            if data.sale_date
            else get_current_time()
        )

        # 5. Sincronizar nombre del canal si se especificó channel_id
        channel = data.channel
        if data.channel_id:
            from app.modules.commerce.channels.models import SalesChannel

            ch = self.session.get(SalesChannel, data.channel_id)
            if ch and ch.name:
                channel = ch.name

        # 6. Atomic Database Transaction
        sale = Sale(
            sale_number=sale_number,
            sheet_sale_id=data.sheet_sale_id,
            sale_date=sale_date,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            channel_id=data.channel_id,
            channel=channel,
            payment_method=data.payment_method,
            payment_status=data.payment_status,
            delivery_modality=data.delivery_modality,
            delivery_address=data.delivery_address,
            delivery_cost=data.delivery_cost,
            delivery_cost_paid_by=data.delivery_cost_paid_by,
            delivery_status=data.delivery_status,
            amount_tendered=amount_tendered,
            change_given=change_given,
            total_collected=final_collected,
            total_cost=round(total_cost, 2),
            net_profit=net_profit,
            currency=data.currency or "BOB",
            observations=data.observations,
        )
        self.session.add(sale)
        self.session.flush()  # Generate sale.id

        affected_batch_ids, affected_round_ids = self._apply_prepared_items(
            sale.id, prepared_items
        )

        self.session.commit()
        self.session.refresh(sale)

        self._sync_affected_batches_and_rounds(
            affected_batch_ids, affected_round_ids
        )
        return sale

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "desc",
        search: str | None = None,
        channel: str | None = None,
        payment_status: str | None = None,
        delivery_status: str | None = None,
    ) -> Sequence[Sale]:
        extra_filters: list[Any] = []
        if channel:
            extra_filters.append(Sale.channel == channel)
        if payment_status:
            extra_filters.append(Sale.payment_status == payment_status)
        if delivery_status:
            extra_filters.append(Sale.delivery_status == delivery_status)

        # Default sort by sale_number desc (latest sale first) if not specified
        if not sort_by:
            sort_by = "sale_number"
            sort_order = "desc"

        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, extra_filters=extra_filters
        )

    def get_by_id(self, id: UUID) -> Sale | None:
        statement = select(Sale).where(Sale.id == id)
        return self.session.exec(statement).first()

    def update(self, id: UUID, data: dict) -> Sale | None:
        sale = self.repository.get_by_id(id)
        if not sale:
            return None

        if "sale_date" in data:
            if data["sale_date"] is None:
                data.pop("sale_date")
            else:
                data["sale_date"] = self._to_naive_local(data["sale_date"])

        if "channel_id" in data and data["channel_id"]:
            from app.modules.commerce.channels.models import SalesChannel

            ch = self.session.get(SalesChannel, data["channel_id"])
            if ch and ch.name:
                data["channel"] = ch.name

        affected_batch_ids: set[UUID] = set()
        affected_round_ids: set[UUID] = set()

        new_items_raw = data.pop("items", None)
        allow_below_minimum = bool(data.pop("allow_below_minimum", False))

        effective_total_collected = sale.total_collected
        effective_total_cost = sale.total_cost

        if new_items_raw is not None:
            parsed_items = [
                it if isinstance(it, SaleItemCreate) else SaleItemCreate(**it)
                for it in new_items_raw
            ]
            if not parsed_items:
                raise BadRequestException(
                    detail="A sale must contain at least one product item"
                )

            existing_items = list(sale.items)
            try:
                old_batches, old_rounds = self._restore_items_stock(existing_items)
                for old_item in existing_items:
                    self.session.delete(old_item)
                self.session.flush()
                self.session.expire(sale, ["items"])

                prepared_items, total_items_price, new_total_cost = (
                    self._prepare_sale_items(parsed_items, allow_below_minimum)
                )
                new_batches, new_rounds = self._apply_prepared_items(
                    sale.id, prepared_items
                )
            except Exception:
                self.session.rollback()
                raise

            effective_total_collected = round(total_items_price, 2)
            effective_total_cost = round(new_total_cost, 2)
            data["total_collected"] = effective_total_collected
            data["total_cost"] = effective_total_cost
            affected_batch_ids = old_batches | new_batches
            affected_round_ids = old_rounds | new_rounds

        # Recalcular efectivo/vuelto autoritativamente según el total real de la venta
        effective_method = data.get("payment_method", sale.payment_method)
        if "amount_tendered" in data:
            incoming_tendered = data["amount_tendered"]
        elif effective_method == "CASH":
            incoming_tendered = sale.amount_tendered
        else:
            incoming_tendered = None

        tendered, change = self._resolve_cash_handling(
            effective_method,
            effective_total_collected,
            incoming_tendered,
        )
        data["amount_tendered"] = tendered
        data["change_given"] = change

        # Recalcular ganancia neta según total, costo y flete
        effective_delivery_cost = (
            data["delivery_cost"]
            if "delivery_cost" in data and data["delivery_cost"] is not None
            else sale.delivery_cost
        )
        effective_paid_by = data.get(
            "delivery_cost_paid_by", sale.delivery_cost_paid_by
        )
        store_delivery = (
            effective_delivery_cost if effective_paid_by == "STORE" else 0.0
        )
        data["net_profit"] = round(
            effective_total_collected - effective_total_cost - store_delivery, 2
        )

        for key, value in data.items():
            setattr(sale, key, value)

        self.session.add(sale)
        self.session.commit()
        self.session.refresh(sale)

        self._sync_affected_batches_and_rounds(
            affected_batch_ids, affected_round_ids
        )
        return sale

    def delete(self, id: UUID) -> bool:
        sale = self.repository.get_by_id(id)
        if not sale:
            return False

        existing_items = list(sale.items)
        affected_batch_ids, affected_round_ids = self._restore_items_stock(
            existing_items
        )
        for item in existing_items:
            self.session.delete(item)
        self.session.flush()
        self.session.expire(sale, ["items"])

        self.session.delete(sale)
        self.session.commit()

        self._sync_affected_batches_and_rounds(
            affected_batch_ids, affected_round_ids
        )
        return True

    def count(
        self,
        search: str | None = None,
        channel: str | None = None,
        payment_status: str | None = None,
        delivery_status: str | None = None,
    ) -> int:
        extra_filters: list[Any] = []
        if channel:
            extra_filters.append(Sale.channel == channel)
        if payment_status:
            extra_filters.append(Sale.payment_status == payment_status)
        if delivery_status:
            extra_filters.append(Sale.delivery_status == delivery_status)

        return self.repository.count(search=search, extra_filters=extra_filters)

    def get_available_products(
        self,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AvailableProductForSale]:
        """Obtiene productos físicos para venta (stock > 0 y status=AVAILABLE).

        Permite búsqueda por nombre, código, marca, modelo o #item_number (#54).
        """
        stmt = (
            select(Product)
            .join(ProductMaster)
            .where(
                Product.status == "AVAILABLE",
                Product.available_quantity > 0,
            )
        )
        if search:
            search_term = f"%{search.strip()}%"
            search_filters: list[Any] = [
                col(ProductMaster.name).ilike(search_term),
                col(ProductMaster.code).ilike(search_term),
                col(ProductMaster.brand).ilike(search_term),
                col(ProductMaster.model).ilike(search_term),
                col(Product.variant_name).ilike(search_term),
            ]
            num = parse_search_int(search, prefixes=("#", "NOV-"))
            if num is not None:
                search_filters.append(col(ProductMaster.item_number) == num)
                search_filters.append(col(Product.sheet_row_id) == num)
            stmt = stmt.where(or_(*search_filters))

        stmt = (
            stmt.order_by(
                col(ProductMaster.item_number).asc(), col(Product.created_at).desc()
            )
            .offset(offset)
            .limit(limit)
        )
        products = self.session.exec(stmt).all()
        result: list[AvailableProductForSale] = []
        for p in products:
            item_prefix = f"#{p.item_number} · " if p.item_number else ""
            variant_str = f" ({p.variant_name})" if p.variant_name else ""
            display_name = f"{item_prefix}{p.name}{variant_str}"
            result.append(
                AvailableProductForSale(
                    id=p.id,
                    master_product_id=p.master_product_id,
                    item_number=p.item_number,
                    code=p.master_code,
                    name=p.name,
                    display_name=display_name,
                    variant_name=p.variant_name,
                    batch_code=p.batch_code,
                    batch_name=p.batch_name,
                    available_quantity=p.available_quantity,
                    published_price=p.effective_published_price,
                    minimum_price=p.effective_minimum_price,
                    official_price=p.official_price,
                    discount_margin=p.discount_margin,
                    currency=p.currency,
                    image_url=p.image_url,
                )
            )
        return result

