import uuid
from typing import Generic, Optional, Sequence, Type, TypeVar, Union

from sqlmodel import Session, SQLModel, select

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Sequence[ModelType]:
        statement = select(self.model)

        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())

        statement = statement.offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def count(self) -> int:
        from sqlmodel import func

        statement = select(func.count()).select_from(self.model)
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
