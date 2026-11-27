"""
Estándar centralizado de filtros, rangos, multiselección y paginación.

Combina Query Parameter Models nativos de FastAPI con especificaciones declarativas
en BaseRepository para garantizar DRY, validación tipada y whitelist de columnas.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Annotated, Any, Mapping
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, Field
from sqlalchemy import DateTime
from sqlmodel import col


def _empty_str_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _parse_multi_str(value: Any) -> list[str] | None:
    if value is None:
        return None
    raw_items = value if isinstance(value, list) else [value]
    parsed = [
        part.strip()
        for item in raw_items
        if item is not None
        for part in str(item).split(",")
        if part.strip()
    ]
    return parsed or None


def _parse_multi_uuid(value: Any) -> list[UUID] | None:
    if value is None:
        return None
    raw_items = value if isinstance(value, list) else [value]
    result: list[UUID] = []
    for item in raw_items:
        if item is None:
            continue
        if isinstance(item, UUID):
            result.append(item)
            continue
        for part in str(item).split(","):
            cleaned = part.strip()
            if cleaned:
                result.append(UUID(cleaned))
    return result or None


OptStr = Annotated[str | None, BeforeValidator(_empty_str_to_none)]
OptBool = Annotated[bool | None, BeforeValidator(_empty_str_to_none)]
OptInt = Annotated[int | None, BeforeValidator(_empty_str_to_none)]
OptFloat = Annotated[float | None, BeforeValidator(_empty_str_to_none)]
OptDate = Annotated[date | None, BeforeValidator(_empty_str_to_none)]
OptUUID = Annotated[UUID | None, BeforeValidator(_empty_str_to_none)]
MultiStr = Annotated[list[str] | None, BeforeValidator(_parse_multi_str)]
MultiUUID = Annotated[list[UUID] | None, BeforeValidator(_parse_multi_uuid)]

_RESERVED_QUERY_KEYS = frozenset({"offset", "limit", "sort_by", "sort_order", "search"})


class FilterOp(str, Enum):
    """Operadores SQL soportados de forma declarativa por BaseRepository."""

    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    GTE = "gte"
    LTE = "lte"
    GT = "gt"
    LT = "lt"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    DATE_FROM = "date_from"
    DATE_TO = "date_to"


@dataclass(frozen=True)
class FilterSpec:
    """Vincula un parámetro de filtro HTTP con una columna del modelo y operador."""

    field: str
    op: FilterOp = FilterOp.EQ


class BaseFilterParams(BaseModel):
    """Base para filtros de módulos (compartida entre listado, /count y reportes)."""

    search: OptStr = None

    def to_filter_dict(self) -> dict[str, Any]:
        """Retorna solo los filtros activos (excluyendo None y paginación/búsqueda)."""
        data = self.model_dump(exclude_none=True)
        return {k: v for k, v in data.items() if k not in _RESERVED_QUERY_KEYS}


class SortQueryMixin(BaseModel):
    """Mixin estándar de ordenamiento para reportes y listados."""

    sort_by: OptStr = None
    sort_order: str = "asc"


class ListQueryMixin(SortQueryMixin):
    """Mixin estándar de paginación y ordenamiento para endpoints GET /."""

    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


class PaginatedResponse[T](BaseModel):
    """Envoltorio estándar opcional para respuestas paginadas unificadas."""

    items: list[T]
    total: int
    offset: int
    limit: int


def _normalize_filter_dict(
    filters: BaseFilterParams | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if filters is None:
        return {}
    if isinstance(filters, BaseFilterParams):
        return filters.to_filter_dict()
    return {
        k: v
        for k, v in filters.items()
        if v is not None and k not in _RESERVED_QUERY_KEYS
    }


def _apply_operator(column: Any, op: FilterOp, value: Any) -> Any | None:
    if op == FilterOp.EQ:
        return column == value
    if op == FilterOp.NEQ:
        return column != value
    if op == FilterOp.IN:
        if not value:
            return None
        return column.in_(value)
    if op == FilterOp.ILIKE:
        return column.ilike(f"%{value}%")
    if op == FilterOp.IS_NULL:
        return column.is_(None) if bool(value) else column.is_not(None)
    if op == FilterOp.GT:
        return column > value
    if op == FilterOp.LT:
        return column < value
    if op in (FilterOp.GTE, FilterOp.DATE_FROM):
        if (
            isinstance(value, date)
            and not isinstance(value, datetime)
            and isinstance(getattr(column, "type", None), DateTime)
        ):
            return column >= datetime.combine(value, time.min)
        return column >= value
    if op in (FilterOp.LTE, FilterOp.DATE_TO):
        if (
            isinstance(value, date)
            and not isinstance(value, datetime)
            and isinstance(getattr(column, "type", None), DateTime)
        ):
            next_day = datetime.combine(value + timedelta(days=1), time.min)
            return column < next_day
        return column <= value
    return None


def build_sqlalchemy_filters(
    model: type[Any],
    filter_fields: Mapping[str, FilterOp | FilterSpec],
    filters: BaseFilterParams | Mapping[str, Any] | None,
) -> list[Any]:
    """Construye cláusulas WHERE SQLAlchemy desde un mapa declarativo."""
    active_filters = _normalize_filter_dict(filters)
    clauses: list[Any] = []

    for param_name, value in active_filters.items():
        spec_or_op = filter_fields.get(param_name)
        if spec_or_op is None:
            continue

        if isinstance(spec_or_op, FilterSpec):
            field_name = spec_or_op.field
            op = spec_or_op.op
        else:
            field_name = param_name
            op = spec_or_op

        if not hasattr(model, field_name):
            continue

        column = col(getattr(model, field_name))
        clause = _apply_operator(column, op, value)
        if clause is not None:
            clauses.append(clause)

    return clauses
