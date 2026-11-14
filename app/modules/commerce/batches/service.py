from typing import Sequence
from uuid import UUID

from sqlmodel import Session, func, select

from app.modules.commerce.batches.models import Batch
from app.modules.commerce.batches.repository import BatchRepository


class BatchService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = BatchRepository(session)

    def _sync_round(self, round_id: UUID | None) -> None:
        if round_id:
            from app.modules.commerce.rounds.service import InvestmentRoundService

            InvestmentRoundService(self.session).recalculate_round(round_id)

    def create(self, data: Batch) -> Batch:
        # Calculate derived fields automatically on creation
        data.total_cost = round(data.purchase_price + data.freight_cost, 2)
        data.sellable_items_count = max(
            0, data.initial_items_count - data.merma_items_count
        )
        if data.sellable_items_count > 0:
            data.unit_cost = round(data.total_cost / data.sellable_items_count, 2)
        else:
            data.unit_cost = 0.0
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
    ) -> Sequence[Batch]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Batch | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Batch | None:
        batch = self.repository.get_by_id(id)
        if not batch:
            return None

        old_round_id = batch.investment_round_id

        # Apply update dictionary
        for key, value in data.items():
            setattr(batch, key, value)

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

        if batch.investment_round_id:
            self._sync_round(batch.investment_round_id)
        if old_round_id and old_round_id != batch.investment_round_id:
            self._sync_round(old_round_id)

        return batch

    def delete(self, id: UUID) -> bool:
        batch = self.repository.get_by_id(id)
        if not batch:
            return False
        round_id = batch.investment_round_id
        deleted = self.repository.delete(id)
        if deleted and round_id:
            self._sync_round(round_id)
        return deleted

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)

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

        if batch.investment_round_id:
            self._sync_round(batch.investment_round_id)

        return batch

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

        # Seleccionar productos vendibles de esta caja (excluyendo mermas)
        stmt = select(Product).where(
            Product.batch_id == batch_id,
            Product.physical_condition != "DAMAGED_SCRAP",
        )
        products = list(self.session.exec(stmt).all())
        if not products:
            return batch

        def get_item_basis_price(prod: Product) -> float:
            val = getattr(prod, basis, 0.0) or 0.0
            if val > 0:
                return float(val)
            for alt in ("published_price", "official_price", "minimum_price"):
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
