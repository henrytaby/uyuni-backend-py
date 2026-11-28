from collections import defaultdict
from typing import Mapping, Sequence
from uuid import UUID

from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from app.core.filters import BaseFilterParams
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.batches.repository import BatchRepository
from app.modules.commerce.batches.schemas import (
    BatchMetricsRead,
    BatchPortfolioReportRead,
    BatchPortfolioSummaryRead,
)
from app.modules.commerce.constants import SalePaymentMethod, SalePaymentStatus
from app.util.datetime import get_current_time


class BatchService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = BatchRepository(session)

    def _sync_round(self, round_id: UUID | None) -> None:
        if round_id:
            from app.modules.commerce.rounds.service import InvestmentRoundService

            InvestmentRoundService(self.session).recalculate_round(round_id)

    def create(self, data: Batch) -> Batch:
        # Autogenerar código secuencial si no se ingresó
        if not data.code or not data.code.strip():
            count = self.session.exec(select(func.count(col(Batch.id)))).one()
            data.code = f"CAJA-{int(count) + 1:02d}"
        else:
            data.code = data.code.strip().upper()

        # Calculate derived fields automatically on creation
        data.total_cost = round(data.purchase_price + data.freight_cost, 2)
        data.sellable_items_count = max(
            0, data.initial_items_count - data.merma_items_count
        )
        if data.sellable_items_count > 0:
            data.unit_cost = round(data.total_cost / data.sellable_items_count, 2)
        else:
            data.unit_cost = 0.0

        if not data.financial_status:
            data.financial_status = "EN_RECUPERACION"

        created = self.repository.create(data)
        if created.investment_round_id:
            self._sync_round(created.investment_round_id)
        return created

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        filters: BaseFilterParams | Mapping[str, object] | None = None,
    ) -> Sequence[Batch]:
        return self.repository.get_all(
            offset,
            limit,
            sort_by,
            sort_order,
            search,
            filters=filters,
        )

    def get_by_id(self, id: UUID) -> Batch | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Batch | None:
        batch = self.repository.get_by_id(id)
        if not batch:
            return None

        old_round_id = batch.investment_round_id

        from app.modules.commerce.products.models import Product

        # Verificar si el lote ya tiene productos físicos asociados
        prods_count = self.session.exec(
            select(func.count(col(Product.id))).where(Product.batch_id == id)
        ).one()

        if prods_count > 0:
            # Los conteos se derivan de los productos, no se sobreescriben a mano
            data.pop("initial_items_count", None)
            data.pop("merma_items_count", None)
            data.pop("sellable_items_count", None)
            data.pop("unit_cost", None)
            data.pop("financial_status", None)

            # Si el costeo es específico (bazar, compras a pedido),
            # purchase_price se suma de los productos
            costing_method = data.get("costing_method", batch.costing_method)
            if costing_method in ("SPECIFIC_ITEM", "ON_DEMAND", "WHOLESALE"):
                data.pop("purchase_price", None)

        # total_cost es siempre estrictamente calculado (purchase_price + freight_cost)
        data.pop("total_cost", None)

        # Apply update dictionary
        for key, value in data.items():
            setattr(batch, key, value)

        # Sincronizar cantidades y costos de productos si ya existen
        if prods_count > 0:
            stmt = select(
                func.coalesce(func.sum(Product.initial_quantity), 0),
                func.coalesce(func.sum(Product.merma_quantity), 0),
            ).where(Product.batch_id == id)
            t_initial, t_merma = self.session.exec(stmt).one()
            batch.initial_items_count = int(t_initial)
            batch.merma_items_count = int(t_merma)

            if batch.costing_method in ("SPECIFIC_ITEM", "ON_DEMAND", "WHOLESALE"):
                prods_stmt = select(Product).where(Product.batch_id == id)
                prods = list(self.session.exec(prods_stmt).all())
                items_cost = sum(
                    (p.cost_price or 0.0) * (p.available_quantity + p.sold_quantity)
                    for p in prods
                )
                if items_cost > 0:
                    batch.purchase_price = round(items_cost, 2)

        # Recalculate totals
        batch.total_cost = round(batch.purchase_price + batch.freight_cost, 2)
        batch.sellable_items_count = max(
            0, batch.initial_items_count - batch.merma_items_count
        )
        if batch.sellable_items_count > 0:
            batch.unit_cost = round(batch.total_cost / batch.sellable_items_count, 2)
        else:
            batch.unit_cost = 0.0

        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)

        # Sincronizar estado financiero del lote
        self.sync_financial_status(batch.id)

        if batch.investment_round_id:
            self._sync_round(batch.investment_round_id)
        if old_round_id and old_round_id != batch.investment_round_id:
            self._sync_round(old_round_id)

        return batch

    def delete(self, id: UUID) -> bool:
        from app.core.exceptions import BadRequestException
        from app.modules.commerce.products.models import Product

        batch = self.repository.get_by_id(id)
        if not batch:
            return False

        # Protección: Validar si tiene productos asociados
        prods_count = self.session.exec(
            select(func.count(col(Product.id))).where(Product.batch_id == id)
        ).one()

        if prods_count > 0:
            raise BadRequestException(
                detail=(
                    f"No se puede eliminar la caja/lote '{batch.name}' ({batch.code}) "
                    f"porque tiene {prods_count} producto(s) asociado(s). "
                    "Desvincule o elimine los productos primero."
                )
            )

        round_id = batch.investment_round_id
        deleted = self.repository.delete(id)
        if deleted and round_id:
            self._sync_round(round_id)
        return deleted

    def count(
        self,
        search: str | None = None,
        filters: BaseFilterParams | Mapping[str, object] | None = None,
    ) -> int:
        return self.repository.count(search, filters=filters)

    def recalculate_from_products(
        self,
        batch_id: UUID,
        revalue_sales: bool = True,
        force_product_counts: bool = False,
    ) -> Batch | None:
        """
        Recalcula automáticamente el conteo de ítems y costo unitario del lote
        a partir de sus productos registrados.

        - Si force_product_counts es True (o initial_items_count == 0):
          Toma directamente los totales sumados de la tabla de productos.
        - Si force_product_counts es False:
          Preserva el conteo inicial del lote si aún está en proceso de desempaque
          (es decir, si initial_items_count > sum(productos)), pero lo expande si
          se desempacan más productos de los previstos.
        """
        batch = self.repository.get_by_id(batch_id)
        if not batch:
            return None

        from app.modules.commerce.products.models import Product

        # Consultar conteos reales agregados de la tabla de productos
        statement = select(
            func.coalesce(func.sum(Product.initial_quantity), 0),
            func.coalesce(func.sum(Product.merma_quantity), 0),
        ).where(Product.batch_id == batch_id)
        total_initial, total_merma = self.session.exec(statement).one()

        t_initial = int(total_initial)
        t_merma = int(total_merma)

        if force_product_counts or batch.initial_items_count == 0:
            batch.initial_items_count = t_initial
            batch.merma_items_count = t_merma
        else:
            # Expandir si se catalogaron más productos de los estimados inicialmente
            if t_initial > batch.initial_items_count:
                batch.initial_items_count = t_initial
            if t_merma > batch.merma_items_count:
                batch.merma_items_count = t_merma

        batch.sellable_items_count = max(
            0, batch.initial_items_count - batch.merma_items_count
        )

        # Si el costeo es directo por ítem (Opción 2 / 3: SPECIFIC_ITEM, ON_DEMAND),
        # calcular purchase_price como la suma de cost_price * cantidad
        if batch.costing_method in ("SPECIFIC_ITEM", "ON_DEMAND", "WHOLESALE"):
            prods_stmt = select(Product).where(Product.batch_id == batch_id)
            prods = list(self.session.exec(prods_stmt).all())
            items_cost = sum(
                (p.cost_price or 0.0) * (p.available_quantity + p.sold_quantity)
                for p in prods
            )
            if items_cost > 0:
                batch.purchase_price = round(items_cost, 2)

        batch.total_cost = round(batch.purchase_price + batch.freight_cost, 2)

        if batch.sellable_items_count > 0:
            batch.unit_cost = round(batch.total_cost / batch.sellable_items_count, 2)
        else:
            batch.unit_cost = 0.0

        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)

        if revalue_sales:
            self.revalue_batch_sales(batch_id, batch.unit_cost)

        # Sincronizar estado financiero del lote
        self.sync_financial_status(batch_id)

        if batch.investment_round_id:
            self._sync_round(batch.investment_round_id)

        return batch

    @staticmethod
    def _resolve_financial_status(total_cost: float, collected_amount: float) -> str:
        if total_cost == 0:
            return "RECUPERADO" if collected_amount > 0 else "EN_RECUPERACION"
        if collected_amount >= total_cost:
            return "RECUPERADO"
        if collected_amount >= (0.8 * total_cost):
            return "CASI_TABLAS"
        return "EN_RECUPERACION"

    def sync_financial_status(self, batch_id: UUID) -> str:
        """
        Calcula y actualiza automáticamente el estado financiero del lote
        (EN_RECUPERACION, CASI_TABLAS, RECUPERADO) según las ventas cobradas.
        """
        batch = self.repository.get_by_id(batch_id)
        if not batch:
            return "EN_RECUPERACION"

        from app.modules.commerce.products.models import Product
        from app.modules.commerce.sales.models import Sale, SaleItem

        sales_stmt = (
            select(func.coalesce(func.sum(SaleItem.total_price), 0.0))
            .join(Product, col(SaleItem.product_id) == col(Product.id))
            .join(Sale, col(SaleItem.sale_id) == col(Sale.id))
            .where(
                col(Product.batch_id) == batch_id,
                col(Sale.payment_status) == SalePaymentStatus.COLLECTED.value,
                col(Sale.payment_method) != SalePaymentMethod.COURTESY.value,
            )
        )
        total_collected = float(self.session.exec(sales_stmt).one())
        status = self._resolve_financial_status(batch.total_cost, total_collected)

        if batch.financial_status != status:
            batch.financial_status = status
            self.session.add(batch)
            self.session.commit()
            self.session.refresh(batch)

        return batch.financial_status

    def _compute_batches_metrics(
        self, batches: Sequence[Batch]
    ) -> list[BatchMetricsRead]:
        """Calcula métricas financieras y proyecciones de stock para N lotes."""
        if not batches:
            return []

        from app.modules.commerce.products.models import Product
        from app.modules.commerce.rounds.models import InvestmentRound
        from app.modules.commerce.sales.models import Sale, SaleItem

        batch_ids = [b.id for b in batches]
        round_ids = list(
            {b.investment_round_id for b in batches if b.investment_round_id}
        )

        rounds_map: dict[UUID, InvestmentRound] = {}
        if round_ids:
            rounds_stmt = select(InvestmentRound).where(
                col(InvestmentRound.id).in_(round_ids)
            )
            rounds_map = {r.id: r for r in self.session.exec(rounds_stmt).all()}

        products_stmt = (
            select(Product)
            .options(selectinload(Product.master_product))  # type: ignore[arg-type]
            .where(col(Product.batch_id).in_(batch_ids))
        )
        products_by_batch: dict[UUID, list[Product]] = defaultdict(list)
        for product in self.session.exec(products_stmt).all():
            if product.batch_id:
                products_by_batch[product.batch_id].append(product)

        sales_stmt = (
            sa_select(
                col(Product.batch_id),
                col(Sale.payment_status),
                col(Sale.payment_method),
                func.coalesce(func.sum(SaleItem.total_price), 0.0),
                func.coalesce(func.sum(SaleItem.unit_cost * SaleItem.quantity), 0.0),
                func.coalesce(func.sum(SaleItem.quantity), 0),
            )
            .select_from(SaleItem)
            .join(Product, col(SaleItem.product_id) == col(Product.id))
            .join(Sale, col(SaleItem.sale_id) == col(Sale.id))
            .where(col(Product.batch_id).in_(batch_ids))
            .group_by(
                col(Product.batch_id),
                col(Sale.payment_status),
                col(Sale.payment_method),
            )
        )

        sales_agg: dict[UUID, dict[str, float | int]] = defaultdict(
            lambda: {
                "collected": 0.0,
                "pending": 0.0,
                "realized_cogs": 0.0,
                "courtesy_items": 0,
                "courtesy_cost": 0.0,
            }
        )
        sales_rows = self.session.execute(sales_stmt).all()
        for b_id, pay_status, pay_method, rev_sum, cost_sum, qty_sum in sales_rows:
            if not b_id:
                continue
            bucket = sales_agg[b_id]
            if pay_status == SalePaymentStatus.REFUNDED.value:
                continue
            if (
                pay_status == SalePaymentStatus.COURTESY.value
                or pay_method == SalePaymentMethod.COURTESY.value
            ):
                bucket["courtesy_items"] = int(bucket["courtesy_items"]) + int(qty_sum)
                bucket["courtesy_cost"] = float(bucket["courtesy_cost"]) + float(
                    cost_sum
                )
            elif pay_status == SalePaymentStatus.COLLECTED.value:
                bucket["collected"] = float(bucket["collected"]) + float(rev_sum)
                bucket["realized_cogs"] = float(bucket["realized_cogs"]) + float(
                    cost_sum
                )
            elif pay_status == SalePaymentStatus.PENDING.value:
                bucket["pending"] = float(bucket["pending"]) + float(rev_sum)

        today = get_current_time().date()
        metrics_list: list[BatchMetricsRead] = []

        for batch in batches:
            round_obj = (
                rounds_map.get(batch.investment_round_id)
                if batch.investment_round_id
                else None
            )
            batch_products = products_by_batch.get(batch.id, [])
            available_items = 0
            sold_items = 0
            rem_min_val = 0.0
            rem_pub_val = 0.0

            for prod in batch_products:
                sold_items += prod.sold_quantity
                is_sellable_stock = (
                    prod.available_quantity > 0 and prod.status != "SCRAPPED"
                )
                if is_sellable_stock:
                    available_items += prod.available_quantity
                    rem_min_val += (
                        prod.available_quantity * prod.effective_minimum_price
                    )
                    rem_pub_val += (
                        prod.available_quantity * prod.effective_published_price
                    )

            agg = sales_agg[batch.id]
            collected_amount = round(float(agg["collected"]), 2)
            pending_amount = round(float(agg["pending"]), 2)
            committed_sales_amount = round(collected_amount + pending_amount, 2)
            realized_cogs = round(float(agg["realized_cogs"]), 2)
            courtesy_items = int(agg["courtesy_items"])
            courtesy_cost = round(float(agg["courtesy_cost"]), 2)

            total_cost = round(batch.total_cost, 2)
            cash_balance = round(collected_amount - total_cost, 2)
            committed_balance = round(committed_sales_amount - total_cost, 2)
            realized_gross_profit = round(collected_amount - realized_cogs, 2)
            realized_gross_margin_pct = (
                round((realized_gross_profit / collected_amount) * 100, 2)
                if collected_amount > 0
                else 0.0
            )
            recovery_pct = (
                round((collected_amount / total_cost) * 100, 2)
                if total_cost > 0
                else (100.0 if collected_amount > 0 else 0.0)
            )
            remaining_to_breakeven = round(max(0.0, total_cost - collected_amount), 2)

            rem_min_val = round(rem_min_val, 2)
            rem_pub_val = round(rem_pub_val, 2)
            proj_min_rev = round(committed_sales_amount + rem_min_val, 2)
            proj_pub_rev = round(committed_sales_amount + rem_pub_val, 2)
            proj_min_profit = round(proj_min_rev - total_cost, 2)
            proj_pub_profit = round(proj_pub_rev - total_cost, 2)
            proj_min_roi = (
                round((proj_min_profit / total_cost) * 100, 2)
                if total_cost > 0
                else 0.0
            )
            proj_pub_roi = (
                round((proj_pub_profit / total_cost) * 100, 2)
                if total_cost > 0
                else 0.0
            )

            days_in_inv = (
                max(0, (today - batch.purchase_date).days)
                if batch.purchase_date
                else None
            )
            financial_status = self._resolve_financial_status(
                total_cost, collected_amount
            )

            metrics_list.append(
                BatchMetricsRead(
                    batch_id=batch.id,
                    code=batch.code,
                    name=batch.name,
                    investment_round_id=batch.investment_round_id,
                    round_code=round_obj.code if round_obj else None,
                    round_name=round_obj.name if round_obj else None,
                    provider=batch.provider,
                    batch_type=batch.batch_type,
                    costing_method=batch.costing_method,
                    purchase_date=batch.purchase_date,
                    days_in_inventory=days_in_inv,
                    status=batch.status,
                    financial_status=financial_status,
                    currency=batch.currency,
                    purchase_price=round(batch.purchase_price, 2),
                    freight_cost=round(batch.freight_cost, 2),
                    total_cost=total_cost,
                    unit_cost=round(batch.unit_cost, 2),
                    initial_items_count=batch.initial_items_count,
                    merma_items_count=batch.merma_items_count,
                    sellable_items_count=batch.sellable_items_count,
                    available_items=available_items,
                    sold_items=sold_items,
                    courtesy_items=courtesy_items,
                    courtesy_cost=courtesy_cost,
                    collected_amount=collected_amount,
                    pending_amount=pending_amount,
                    committed_sales_amount=committed_sales_amount,
                    cash_balance=cash_balance,
                    committed_balance=committed_balance,
                    realized_cogs=realized_cogs,
                    realized_gross_profit=realized_gross_profit,
                    realized_gross_margin_percent=realized_gross_margin_pct,
                    recovery_progress_percent=recovery_pct,
                    remaining_to_breakeven=remaining_to_breakeven,
                    remaining_stock_min_value=rem_min_val,
                    remaining_stock_published_value=rem_pub_val,
                    projected_total_min_revenue=proj_min_rev,
                    projected_total_published_revenue=proj_pub_rev,
                    projected_min_net_profit=proj_min_profit,
                    projected_published_net_profit=proj_pub_profit,
                    projected_min_roi_percent=proj_min_roi,
                    projected_published_roi_percent=proj_pub_roi,
                )
            )

        return metrics_list

    def get_batch_metrics(self, batch_id: UUID) -> BatchMetricsRead | None:
        """Retorna métricas financieras y proyecciones de stock de un lote."""
        batch = self.repository.get_by_id(batch_id)
        if not batch:
            return None
        return self._compute_batches_metrics([batch])[0]

    def get_portfolio_metrics(
        self,
        filters: BaseFilterParams | Mapping[str, object] | None = None,
        search: str | None = None,
        sort_by: str | None = "purchase_date",
        sort_order: str = "desc",
    ) -> BatchPortfolioReportRead:
        """Retorna métricas consolidadas del portafolio de lotes y su detalle."""
        batches = self.repository.get_all(
            offset=0,
            limit=500,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            filters=filters,
        )
        items = self._compute_batches_metrics(batches)

        total_cost = round(sum(it.total_cost for it in items), 2)
        collected_amount = round(sum(it.collected_amount for it in items), 2)
        pending_amount = round(sum(it.pending_amount for it in items), 2)
        committed_sales = round(sum(it.committed_sales_amount for it in items), 2)
        realized_cogs = round(sum(it.realized_cogs for it in items), 2)
        rem_min_val = round(sum(it.remaining_stock_min_value for it in items), 2)
        rem_pub_val = round(sum(it.remaining_stock_published_value for it in items), 2)
        proj_min_rev = round(committed_sales + rem_min_val, 2)
        proj_pub_rev = round(committed_sales + rem_pub_val, 2)

        recovery_pct = (
            round((collected_amount / total_cost) * 100, 2)
            if total_cost > 0
            else (100.0 if collected_amount > 0 else 0.0)
        )

        summary = BatchPortfolioSummaryRead(
            total_batches=len(items),
            recovered_batches=sum(
                1 for it in items if it.financial_status == "RECUPERADO"
            ),
            near_breakeven_batches=sum(
                1 for it in items if it.financial_status == "CASI_TABLAS"
            ),
            in_recovery_batches=sum(
                1 for it in items if it.financial_status == "EN_RECUPERACION"
            ),
            currency=items[0].currency if items else "BOB",
            total_purchase_price=round(sum(it.purchase_price for it in items), 2),
            total_freight_cost=round(sum(it.freight_cost for it in items), 2),
            total_cost=total_cost,
            initial_items_count=sum(it.initial_items_count for it in items),
            merma_items_count=sum(it.merma_items_count for it in items),
            sellable_items_count=sum(it.sellable_items_count for it in items),
            available_items=sum(it.available_items for it in items),
            sold_items=sum(it.sold_items for it in items),
            courtesy_items=sum(it.courtesy_items for it in items),
            courtesy_cost=round(sum(it.courtesy_cost for it in items), 2),
            collected_amount=collected_amount,
            pending_amount=pending_amount,
            committed_sales_amount=committed_sales,
            cash_balance=round(collected_amount - total_cost, 2),
            committed_balance=round(committed_sales - total_cost, 2),
            realized_cogs=realized_cogs,
            realized_gross_profit=round(collected_amount - realized_cogs, 2),
            recovery_progress_percent=recovery_pct,
            remaining_to_breakeven=round(max(0.0, total_cost - collected_amount), 2),
            remaining_stock_min_value=rem_min_val,
            remaining_stock_published_value=rem_pub_val,
            projected_total_min_revenue=proj_min_rev,
            projected_total_published_revenue=proj_pub_rev,
            projected_min_net_profit=round(proj_min_rev - total_cost, 2),
            projected_published_net_profit=round(proj_pub_rev - total_cost, 2),
        )

        return BatchPortfolioReportRead(summary=summary, items=items)

    def revalue_batch_sales(self, batch_id: UUID, new_unit_cost: float) -> int:
        """
        Revalúa todas las ventas históricas asociadas a este lote.
        Actualiza sale_item.unit_cost, net_margin, y el total_cost y net_profit.
        Retorna la cantidad de ventas recalculadas.
        """
        from app.modules.commerce.products.models import Product
        from app.modules.commerce.sales.models import Sale, SaleItem

        # Buscar ítems de ventas para productos pertenecientes a esta caja
        stmt = select(SaleItem).join(Product).where(Product.batch_id == batch_id)
        sale_items = self.session.exec(stmt).all()

        affected_sale_ids: set[UUID] = set()
        for item in sale_items:
            item.unit_cost = new_unit_cost
            item.net_margin = round(
                item.total_price - (new_unit_cost * item.quantity), 2
            )
            self.session.add(item)
            affected_sale_ids.add(item.sale_id)

        self.session.flush()

        # Recalcular las ventas cabecera afectadas
        for sale_id in affected_sale_ids:
            sale = self.session.get(Sale, sale_id)
            if not sale:
                continue
            all_items_stmt = select(SaleItem).where(SaleItem.sale_id == sale_id)
            all_items = self.session.exec(all_items_stmt).all()
            recalculated_total_cost = round(
                sum(it.unit_cost * it.quantity for it in all_items), 2
            )
            sale.total_cost = recalculated_total_cost
            sale.net_profit = round(sale.total_collected - recalculated_total_cost, 2)
            self.session.add(sale)

        self.session.commit()
        return len(affected_sale_ids)

    def allocate_relative_costs(
        self,
        batch_id: UUID,
        basis: str = "published_price",
        revalue_sales: bool = True,
    ) -> Batch | None:
        """
        Distribuye proporcionalmente el costo total de la caja entre todos sus
        productos vendibles (Retail Inventory Method), garantizando que la suma
        de costos sea exactamente igual al costo total de la caja al centavo.

        - basis: 'published_price', 'official_price' o 'minimum_price'.
        - revalue_sales: Si es True, recalcula costos y márgenes de ventas.
        """
        batch = self.repository.get_by_id(batch_id)
        if not batch:
            return None

        from app.modules.commerce.products.models import Product

        # Seleccionar productos vendibles o vendidos (excluyendo mermas totales)
        stmt = select(Product).where(
            Product.batch_id == batch_id,
            Product.status != "SCRAPPED",
            (col(Product.available_quantity) + col(Product.sold_quantity)) > 0,
        )
        products = list(self.session.exec(stmt).all())
        if not products:
            return batch

        def get_item_basis_price(prod: Product) -> float:
            if basis == "published_price":
                val = prod.effective_published_price
            elif basis == "minimum_price":
                val = prod.effective_minimum_price
            else:
                val = getattr(prod, basis, 0.0) or 0.0
            if val > 0:
                return float(val)
            for alt in (
                "effective_published_price",
                "official_price",
                "effective_minimum_price",
            ):
                alt_val = getattr(prod, alt, 0.0) or 0.0
                if alt_val > 0:
                    return float(alt_val)
            return 0.0

        # Calcular el valor total ponderado base
        total_basis = 0.0
        product_quantities: dict[UUID, int] = {}
        for p in products:
            qty = p.available_quantity + p.sold_quantity
            product_quantities[p.id] = qty
            price_val = get_item_basis_price(p)
            total_basis += price_val * qty

        if total_basis <= 0:
            flat_cost = batch.unit_cost
            for p in products:
                p.cost_price = flat_cost
                self.session.add(p)
            self.session.commit()
            if revalue_sales:
                self.revalue_batch_sales(batch_id, flat_cost)
            if batch.investment_round_id:
                self._sync_round(batch.investment_round_id)
            return batch

        cost_factor = batch.total_cost / total_basis
        allocated_total = 0.0

        # Asignar costo proporcional a cada producto excepto el último
        for p in products[:-1]:
            qty = product_quantities[p.id]
            price_val = get_item_basis_price(p)

            item_cost = round(price_val * cost_factor, 2)
            p.cost_price = item_cost
            allocated_total = round(allocated_total + (item_cost * qty), 2)
            self.session.add(p)

        # Reconciliación de centavos con el último producto
        last_p = products[-1]
        last_qty = max(1, product_quantities[last_p.id])
        remaining_cost = round(batch.total_cost - allocated_total, 2)
        last_item_cost = round(remaining_cost / last_qty, 2)
        last_p.cost_price = last_item_cost
        self.session.add(last_p)

        self.session.commit()
        self.session.refresh(batch)

        if revalue_sales:
            self._revalue_sales_by_product_costs(batch_id)

        if batch.investment_round_id:
            self._sync_round(batch.investment_round_id)

        return batch

    def _revalue_sales_by_product_costs(self, batch_id: UUID) -> int:
        """
        Revalúa ventas históricas de un lote usando el cost_price específico.
        """
        from app.modules.commerce.products.models import Product
        from app.modules.commerce.sales.models import Sale, SaleItem

        stmt = select(SaleItem).join(Product).where(Product.batch_id == batch_id)
        sale_items = self.session.exec(stmt).all()

        affected_sale_ids: set[UUID] = set()
        for item in sale_items:
            prod = self.session.get(Product, item.product_id)
            if not prod:
                continue
            item_cost = prod.cost_price if prod.cost_price is not None else 0.0
            item.unit_cost = item_cost
            item.net_margin = round(item.total_price - (item_cost * item.quantity), 2)
            self.session.add(item)
            affected_sale_ids.add(item.sale_id)

        self.session.flush()

        for sale_id in affected_sale_ids:
            sale = self.session.get(Sale, sale_id)
            if not sale:
                continue
            all_items_stmt = select(SaleItem).where(SaleItem.sale_id == sale_id)
            all_items = self.session.exec(all_items_stmt).all()
            recalculated_total_cost = round(
                sum(it.unit_cost * it.quantity for it in all_items), 2
            )
            sale.total_cost = recalculated_total_cost
            sale.net_profit = round(sale.total_collected - recalculated_total_cost, 2)
            self.session.add(sale)

        self.session.commit()
        return len(affected_sale_ids)
