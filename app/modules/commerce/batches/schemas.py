from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.filters import (
    BaseFilterParams,
    ListQueryMixin,
    MultiStr,
    MultiUUID,
    OptBool,
    OptDate,
    OptFloat,
    OptStr,
    OptUUID,
    SortQueryMixin,
)


class BatchFilterParams(BaseFilterParams):
    """Filtros estándar reutilizados en listado, conteo y reporte de portafolio."""

    investment_round_id: OptUUID = None
    investment_round_ids: MultiUUID = None
    without_round: OptBool = None
    status: OptStr = None
    statuses: MultiStr = None
    financial_status: OptStr = None
    financial_statuses: MultiStr = None
    costing_method: OptStr = None
    purchase_date_from: OptDate = None
    purchase_date_to: OptDate = None
    min_total_cost: OptFloat = None
    max_total_cost: OptFloat = None


class BatchListQuery(ListQueryMixin, BatchFilterParams):
    """Query params completos para listado paginado de lotes."""


class BatchPortfolioQuery(SortQueryMixin, BatchFilterParams):
    """Query params para reporte de portafolio de lotes."""

    sort_by: OptStr = "purchase_date"
    sort_order: str = "desc"


class BatchBase(BaseModel):
    code: str | None = None
    name: str
    investment_round_id: UUID | None = None
    provider: str | None = None
    batch_type: str | None = None
    costing_method: str = "WEIGHTED_RETAIL"
    purchase_date: date | None = None
    purchase_price: float = 0.0
    freight_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "BOB"
    initial_items_count: int = 0
    merma_items_count: int = 0
    sellable_items_count: int = 0
    unit_cost: float = 0.0
    status: str = "active"
    financial_status: str = "EN_RECUPERACION"
    observations: str | None = None


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    investment_round_id: UUID | None = None
    provider: str | None = None
    batch_type: str | None = None
    costing_method: str | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    freight_cost: float | None = None
    total_cost: float | None = None
    currency: str | None = None
    initial_items_count: int | None = None
    merma_items_count: int | None = None
    sellable_items_count: int | None = None
    unit_cost: float | None = None
    status: str | None = None
    financial_status: str | None = None
    observations: str | None = None


class BatchRead(BatchBase):
    id: UUID


class BatchMetricsRead(BaseModel):
    """Métricas financieras, de flujo de caja e inventario proyectado de un lote."""

    batch_id: UUID
    code: str
    name: str
    investment_round_id: UUID | None = None
    round_code: str | None = None
    round_name: str | None = None
    provider: str | None = None
    batch_type: str | None = None
    costing_method: str
    purchase_date: date | None = None
    days_in_inventory: int | None = None
    status: str
    financial_status: str
    currency: str

    # Costos e inventario físico
    purchase_price: float
    freight_cost: float
    total_cost: float
    unit_cost: float
    initial_items_count: int
    merma_items_count: int
    sellable_items_count: int
    available_items: int
    sold_items: int
    courtesy_items: int
    courtesy_cost: float

    # Flujo de caja y rentabilidad realizada
    collected_amount: float
    pending_amount: float
    committed_sales_amount: float
    cash_balance: float
    committed_balance: float
    realized_cogs: float
    realized_gross_profit: float
    realized_gross_margin_percent: float
    recovery_progress_percent: float
    remaining_to_breakeven: float

    # Valorización de stock restante y proyecciones (Conservadora vs Objetivo)
    remaining_stock_min_value: float
    remaining_stock_published_value: float
    projected_total_min_revenue: float
    projected_total_published_revenue: float
    projected_min_net_profit: float
    projected_published_net_profit: float
    projected_min_roi_percent: float
    projected_published_roi_percent: float


class BatchPortfolioSummaryRead(BaseModel):
    """Totales consolidados del portafolio de lotes para KPIs y fila resumen."""

    total_batches: int
    recovered_batches: int
    near_breakeven_batches: int
    in_recovery_batches: int
    currency: str = "BOB"

    total_purchase_price: float
    total_freight_cost: float
    total_cost: float
    initial_items_count: int
    merma_items_count: int
    sellable_items_count: int
    available_items: int
    sold_items: int
    courtesy_items: int
    courtesy_cost: float

    collected_amount: float
    pending_amount: float
    committed_sales_amount: float
    cash_balance: float
    committed_balance: float
    realized_cogs: float
    realized_gross_profit: float
    recovery_progress_percent: float
    remaining_to_breakeven: float

    remaining_stock_min_value: float
    remaining_stock_published_value: float
    projected_total_min_revenue: float
    projected_total_published_revenue: float
    projected_min_net_profit: float
    projected_published_net_profit: float


class BatchPortfolioReportRead(BaseModel):
    """Respuesta completa del reporte financiero de portafolio de lotes."""

    summary: BatchPortfolioSummaryRead
    items: list[BatchMetricsRead]
