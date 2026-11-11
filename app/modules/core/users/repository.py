import uuid
from typing import Any, Optional, Sequence

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.models.user import User, UserRole


class UserRepository(BaseRepository[User]):
    searchable_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
        "city",
    ]

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_id(self, id: uuid.UUID | int) -> User | None:
        statement = (
            select(User)
            .where(User.id == id)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role)  # type: ignore[arg-type]
            )
        )
        return self.session.exec(statement).first()

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        extra_filters: Optional[list[Any]] = None,
    ) -> Sequence[User]:
        statement = select(User).options(
            selectinload(User.user_roles).selectinload(UserRole.role)  # type: ignore[arg-type]
        )
        statement = self._apply_search(statement, search)
        if extra_filters:
            statement = statement.where(*extra_filters)
        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())
        statement = statement.offset(offset).limit(limit)
        results: Sequence[User] = self.session.exec(statement).all()
        return list(results)
