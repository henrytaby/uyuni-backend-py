from typing import Any, Sequence
from uuid import UUID

from sqlmodel import Session, col, or_, select

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product
from app.modules.commerce.sales.models import Sale, SaleItem
from app.modules.commerce.sales.repository import SaleItemRepository, SaleRepository
from app.modules.commerce.sales.schemas import AvailableProductForSale, SaleCreate
from app.util.datetime import get_current_time


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

    def create(self, data: SaleCreate) -> Sale:
        if not data.items:
            raise BadRequestException(
                detail="A sale must contain at least one product item"
            )

        # 1. Validation & Pre-computation phase
        prepared_items: list[dict[str, Any]] = []
        total_items_price = 0.0
        total_cost = 0.0

        for item_data in data.items:
            product = self.session.get(Product, item_data.product_id)
            if not product:
                raise NotFoundException(
                    detail=f"Product with ID '{item_data.product_id}' not found"
                )

            # Check stock availability
            if product.available_quantity < item_data.quantity:
                msg = (
                    f"Stock insuficiente para '{product.name}'. "
                    f"Disponible: {product.available_quantity}, "
                    f"Solicitado: {item_data.quantity}"
                )
                raise BadRequestException(detail=msg)

            # Business rule: check minimum price threshold
            effective_min = product.effective_minimum_price
            if (
                effective_min > 0
                and item_data.unit_price < effective_min
                and not data.allow_below_minimum
            ):
                msg = (
                    f"Precio pactado ({item_data.unit_price}) menor al mínimo "
                    f"({effective_min}) para '{product.name}'. "
                    "Requiere autorización (allow_below_minimum=True)."
                )
                raise BadRequestException(detail=msg)

            # Lookup unit cost: 1. Specific cost_price, 2. Batch unit_cost
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

        # 4. Handle cash tendered and change given
        amount_tendered = data.amount_tendered
        change_given = data.change_given
        if amount_tendered is None:
            amount_tendered = final_collected
            change_given = 0.0
        elif change_given is None:
            if amount_tendered >= final_collected:
                change_given = round(amount_tendered - final_collected, 2)
            else:
                change_given = 0.0

        sale_date = data.sale_date or get_current_time()

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

        for p_item in prepared_items:
            product = p_item["product"]
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=p_item["quantity"],
                unit_price=p_item["unit_price"],
                unit_cost=p_item["unit_cost"],
                total_price=p_item["total_price"],
                net_margin=p_item["net_margin"],
            )
            self.session.add(sale_item)

            # Atomic decrement of stock
            product.sold_quantity += p_item["quantity"]
            product.available_quantity = (
                product.initial_quantity
                - product.sold_quantity
                - product.merma_quantity
            )
            if product.available_quantity <= 0:
                product.status = "SOLD_OUT"

            self.session.add(product)

        # Sincronizar lotes y rondas de inversión afectadas por los productos vendidos
        affected_batch_ids: set[UUID] = set()
        affected_round_ids: set[UUID] = set()
        for p_item in prepared_items:
            prod = p_item["product"]
            if prod.batch_id:
                affected_batch_ids.add(prod.batch_id)
                batch = self.session.get(Batch, prod.batch_id)
                if batch and batch.investment_round_id:
                    affected_round_ids.add(batch.investment_round_id)

        self.session.commit()
        self.session.refresh(sale)

        if affected_batch_ids:
            from app.modules.commerce.batches.service import BatchService

            batch_service = BatchService(self.session)
            for b_id in affected_batch_ids:
                batch_service.sync_financial_status(b_id)

        if affected_round_ids:
            from app.modules.commerce.rounds.service import InvestmentRoundService

            round_service = InvestmentRoundService(self.session)
            for r_id in affected_round_ids:
                round_service.recalculate_round(r_id)

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

        # Default sort by sale_date desc if not specified
        if not sort_by:
            sort_by = "sale_date"
            sort_order = "desc"

        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, extra_filters=extra_filters
        )

    def get_by_id(self, id: UUID) -> Sale | None:
        statement = select(Sale).where(Sale.id == id)
        return self.session.exec(statement).first()

    def update(self, id: UUID, data: dict) -> Sale | None:
        if "channel_id" in data and data["channel_id"]:
            from app.modules.commerce.channels.models import SalesChannel

            ch = self.session.get(SalesChannel, data["channel_id"])
            if ch and ch.name:
                data["channel"] = ch.name
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

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
            cleaned = (
                search.strip()
                .replace("#", "")
                .replace("NOV-", "")
                .replace("nov-", "")
                .strip()
            )
            if cleaned.isdigit():
                num = int(cleaned)
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
        return [
            AvailableProductForSale(
                id=p.id,
                master_product_id=p.master_product_id,
                item_number=p.item_number,
                code=p.master_code,
                name=p.name,
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
            for p in products
        ]

