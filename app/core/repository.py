import uuid
from typing import Any, Mapping, Optional, Sequence, Type

from sqlalchemy import String, cast
from sqlmodel import Session, SQLModel, col, func, or_, select

from app.core.filters import (
    BaseFilterParams,
    FilterOp,
    FilterSpec,
    accent_insensitive_ilike,
    build_sqlalchemy_filters,
)


class BaseRepository[ModelType: SQLModel]:
    searchable_fields: list[str] = []
    filter_fields: dict[str, FilterOp | FilterSpec] = {}

    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def _apply_filters(
        self,
        statement: Any,
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
        extra_filters: Optional[list[Any]] = None,
    ) -> Any:
        clauses = build_sqlalchemy_filters(self.model, self.filter_fields, filters)
        if clauses:
            statement = statement.where(*clauses)
        if extra_filters:
            statement = statement.where(*extra_filters)
        return statement

    def _apply_search(self, statement, search: Optional[str]):
        cleaned = search.strip() if search else ""
        if cleaned and self.searchable_fields:
            search_filters = []
            for field in self.searchable_fields:
                if not hasattr(self.model, field):
                    continue

                column = getattr(self.model, field)
                # Cast all fields to String for a true "Global Search"
                # This handles mixed types (int, float) in PostgreSQL
                try:
                    target = col(column)
                    search_filters.append(
                        accent_insensitive_ilike(cast(target, String), cleaned)
                    )
                except Exception:
                    search_filters.append(
                        accent_insensitive_ilike(cast(column, String), cleaned)
                    )

            if search_filters:
                statement = statement.where(or_(*search_filters))
        return statement

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        extra_filters: Optional[list[Any]] = None,
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> Sequence[ModelType]:
        statement = select(self.model)

        # Apply generic search and declarative filters
        statement = self._apply_search(statement, search)
        statement = self._apply_filters(
            statement, filters=filters, extra_filters=extra_filters
        )

        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())

        # Proteger contra ataques DoS de memoria acotando el límite entre 1 y 500
        safe_limit = min(max(1, limit), 500) if limit is not None else 100
        statement = statement.offset(offset).limit(safe_limit)
        return self.session.exec(statement).all()  # type: ignore[no-any-return]

    def count(
        self,
        search: Optional[str] = None,
        extra_filters: Optional[list[Any]] = None,
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> int:
        statement = select(func.count()).select_from(self.model)

        # Apply generic search and declarative filters to count
        statement = self._apply_search(statement, search)
        statement = self._apply_filters(
            statement, filters=filters, extra_filters=extra_filters
        )

        result = self.session.exec(statement).one()
        return int(result)  # type: ignore[arg-type]

    def get_by_id(self, id: uuid.UUID | int) -> Optional[ModelType]:
        return self.session.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, id: uuid.UUID | int, obj_data: dict) -> Optional[ModelType]:
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None

        for key, value in obj_data.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def delete(self, id: uuid.UUID | int) -> bool:
        db_obj = self.get_by_id(id)
        if not db_obj:
            return False

        self.session.delete(db_obj)
        self.session.commit()
        return True
