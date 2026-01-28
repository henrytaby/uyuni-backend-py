import uuid
from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar, Union

from sqlalchemy import String, cast
from sqlmodel import Session, SQLModel, col, func, or_, select

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    searchable_fields: List[str] = []

    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def _apply_search(self, statement, search: Optional[str]):
        if search and self.searchable_fields:
            search_filters = []
            for field in self.searchable_fields:
                if not hasattr(self.model, field):
                    continue

                column = getattr(self.model, field)
                # Cast all fields to String for a true "Global Search"
                # This handles mixed types (int, float) in PostgreSQL
                try:
                    target = col(column)
                    search_filters.append(cast(target, String).ilike(f"%{search}%"))
                except Exception:
                    search_filters.append(cast(column, String).ilike(f"%{search}%"))

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
        extra_filters: Optional[List[Any]] = None,
    ) -> Sequence[ModelType]:
        statement = select(self.model)

        # Apply generic search
        statement = self._apply_search(statement, search)

        # Apply extra filters if provided
        if extra_filters:
            statement = statement.where(*extra_filters)

        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())

        statement = statement.offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def count(
        self, search: Optional[str] = None, extra_filters: Optional[List[Any]] = None
    ) -> int:
        statement = select(func.count()).select_from(self.model)

        # Apply generic search to count
        statement = self._apply_search(statement, search)

        # Apply extra filters to count
        if extra_filters:
            statement = statement.where(*extra_filters)

        return self.session.exec(statement).one()

    def get_by_id(self, id: Union[uuid.UUID, int]) -> Optional[ModelType]:
        return self.session.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, id: Union[uuid.UUID, int], obj_data: dict) -> Optional[ModelType]:
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None

        for key, value in obj_data.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def delete(self, id: Union[uuid.UUID, int]) -> bool:
        db_obj = self.get_by_id(id)
        if not db_obj:
            return False

        self.session.delete(db_obj)
        self.session.commit()
        return True
