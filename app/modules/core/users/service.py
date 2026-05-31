from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from app.auth.utils import get_password_hash
from app.core.exceptions import BadRequestException
from app.models.user import User
from app.modules.core.users.repository import UserRepository


class UserService:
    def __init__(self, session: Session):
        self.repository = UserRepository(session)
        self.session = session

    def _build_filters(
        self,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> list:
        filters = []
        if is_active is not None:
            filters.append(User.is_active == is_active)
        if is_superuser is not None:
            filters.append(User.is_superuser == is_superuser)
        return filters

    def create(self, data: User, password: str) -> User:
        # Check unique username
        query_username = select(User).where(User.username == data.username)
        if self.session.exec(query_username).first():
            raise BadRequestException(detail="Username already registered")

        # Check unique email
        query_email = select(User).where(User.email == data.email)
        if self.session.exec(query_email).first():
            raise BadRequestException(detail="Email already registered")

        # Set password hash
        data.password_hash = get_password_hash(password)

        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> Sequence[User]:
        filters = self._build_filters(is_active, is_superuser)
        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, extra_filters=filters
        )

    def get_by_id(self, id: UUID) -> User | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data_dict: dict) -> User | None:
        db_user = self.get_by_id(id)
        if not db_user:
            return None

        # Check unique username if updated
        if "username" in data_dict and data_dict["username"] != db_user.username:
            query_username = select(User).where(User.username == data_dict["username"])
            if self.session.exec(query_username).first():
                raise BadRequestException(detail="Username already registered")

        # Check unique email if updated
        if "email" in data_dict and data_dict["email"] != db_user.email:
            query_email = select(User).where(User.email == data_dict["email"])
            if self.session.exec(query_email).first():
                raise BadRequestException(detail="Email already registered")

        # Handle password hashing
        if "password" in data_dict:
            password = data_dict.pop("password")
            if password:
                data_dict["password_hash"] = get_password_hash(password)

        return self.repository.update(id, data_dict)

    def delete(self, id: UUID) -> bool:
        # Perform delete matching repository implementation
        return self.repository.delete(id)


    def count(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> int:
        filters = self._build_filters(is_active, is_superuser)
        return self.repository.count(search, extra_filters=filters)
