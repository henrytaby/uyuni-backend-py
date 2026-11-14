from typing import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.core.exceptions import BadRequestException
from app.modules.commerce.rounds.models import InvestmentRound
from app.modules.commerce.rounds.repository import InvestmentRoundRepository


class InvestmentRoundService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = InvestmentRoundRepository(session)

    def create(self, data: InvestmentRound) -> InvestmentRound:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> Sequence[InvestmentRound]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> InvestmentRound | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> InvestmentRound | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        from app.modules.commerce.batches.models import Batch

        round_obj = self.repository.get_by_id(id)
        if not round_obj:
            return False

        # Validar si tiene lotes/cajas asociadas
        batches_count = self.session.exec(
            select(func.count(col(Batch.id))).where(Batch.investment_round_id == id)
        ).one()

        if batches_count > 0:
            raise BadRequestException(
                detail=(
                    f"No se puede eliminar la ronda '{round_obj.name}' "
                    f"({round_obj.code}) porque tiene {batches_count} "
                    "lote(s) asociado(s). Desvincule o elimine los lotes primero."
                )
            )

        return self.repository.delete(id)

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)

    def recalculate_round(self, round_id: UUID) -> InvestmentRound | None:
        """
        Recalcula automáticamente el capital invertido y el estado de la ronda
        a partir de sus lotes asociados (commerce_batch) y ventas registradas.
        """
        round_obj = self.repository.get_by_id(round_id)
        if not round_obj:
            return None

        from app.modules.commerce.batches.models import Batch
        from app.modules.commerce.products.models import Product
        from app.modules.commerce.sales.models import SaleItem

        # 1. Total capital invertido = suma de total_cost de los lotes de la ronda
        batches_stmt = select(Batch).where(Batch.investment_round_id == round_id)
        batches = list(self.session.exec(batches_stmt).all())
        total_invested = round(sum(b.total_cost for b in batches), 2)
        round_obj.capital_invested = total_invested

        # 2. Capital recuperado = suma de ventas de productos asociados a estos lotes
        batch_ids = [b.id for b in batches]
        capital_recovered = 0.0
        total_available_qty = 0
        total_sellable_qty = 0

        if batch_ids:
            sales_stmt = (
                select(func.coalesce(func.sum(SaleItem.total_price), 0.0))
                .join(Product)
                .where(col(Product.batch_id).in_(batch_ids))
            )
            capital_recovered = float(self.session.exec(sales_stmt).one())

            qty_stmt = select(
                func.coalesce(func.sum(Product.available_quantity), 0),
                func.coalesce(
                    func.sum(Product.initial_quantity - Product.merma_quantity), 0
                ),
            ).where(col(Product.batch_id).in_(batch_ids))
            avail_q, sellable_q = self.session.exec(qty_stmt).one()
            total_available_qty = int(avail_q)
            total_sellable_qty = int(sellable_q)

        # 3. Determinar status financiero
        if total_invested == 0:
            if total_available_qty == 0 and total_sellable_qty > 0:
                round_obj.status = "LIQUIDATED"
            elif capital_recovered > 0:
                round_obj.status = "RECOVERED"
            else:
                round_obj.status = "ACTIVE"
        elif capital_recovered >= total_invested:
            if total_available_qty == 0 and total_sellable_qty > 0:
                round_obj.status = "LIQUIDATED"
            else:
                round_obj.status = "RECOVERED"
        elif capital_recovered >= (0.8 * total_invested):
            round_obj.status = "NEAR_BREAKEVEN"
        elif capital_recovered > 0:
            round_obj.status = "IN_RECOVERY"
        else:
            round_obj.status = "ACTIVE"

        self.session.add(round_obj)
        self.session.commit()
        self.session.refresh(round_obj)
        return round_obj

    def get_round_metrics(self, round_id: UUID) -> dict | None:
        """
        Retorna el resumen financiero y métricas de recuperación de la ronda.
        """
        round_obj = self.repository.get_by_id(round_id)
        if not round_obj:
            return None

        from app.modules.commerce.batches.models import Batch
        from app.modules.commerce.products.models import Product
        from app.modules.commerce.sales.models import SaleItem

        batches_stmt = select(Batch).where(Batch.investment_round_id == round_id)
        batches = list(self.session.exec(batches_stmt).all())
        batch_ids = [b.id for b in batches]

        capital_invested = round(sum(b.total_cost for b in batches), 2)
        capital_recovered = 0.0
        total_items = 0
        available_items = 0
        sold_items = 0
        merma_items = 0

        if batch_ids:
            sales_stmt = (
                select(func.coalesce(func.sum(SaleItem.total_price), 0.0))
                .join(Product)
                .where(col(Product.batch_id).in_(batch_ids))
            )
            capital_recovered = round(float(self.session.exec(sales_stmt).one()), 2)

            counts_stmt = select(
                func.coalesce(func.sum(Product.initial_quantity), 0),
                func.coalesce(func.sum(Product.available_quantity), 0),
                func.coalesce(func.sum(Product.sold_quantity), 0),
                func.coalesce(func.sum(Product.merma_quantity), 0),
            ).where(col(Product.batch_id).in_(batch_ids))
            t_tot, t_avail, t_sold, t_merma = self.session.exec(counts_stmt).one()
            total_items = int(t_tot)
            available_items = int(t_avail)
            sold_items = int(t_sold)
            merma_items = int(t_merma)

        net_profit = round(capital_recovered - capital_invested, 2)
        progress_pct = (
            round((capital_recovered / capital_invested) * 100, 2)
            if capital_invested > 0
            else (100.0 if capital_recovered > 0 else 0.0)
        )

        return {
            "round_id": round_obj.id,
            "code": round_obj.code,
            "name": round_obj.name,
            "status": round_obj.status,
            "capital_invested": capital_invested,
            "capital_recovered": capital_recovered,
            "net_profit": net_profit,
            "break_even_progress_percent": progress_pct,
            "is_break_even": (
                capital_recovered >= capital_invested and capital_invested > 0
            ),
            "batches_count": len(batches),
            "total_items": total_items,
            "available_items": available_items,
            "sold_items": sold_items,
            "merma_items": merma_items,
        }
