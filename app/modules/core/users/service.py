from typing import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.auth.utils import get_password_hash
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.role import Role
from app.models.user import User, UserLogLogin, UserRole
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

    def _validate_role_slugs(self, role_slugs: list[str]) -> list[Role]:
        validated_roles: list[Role] = []
        for slug in role_slugs:
            role_obj = self.session.exec(
                select(Role).where(Role.slug == slug, Role.is_active == True)  # noqa: E712
            ).first()
            if not role_obj:
                raise BadRequestException(detail=f"Role '{slug}' not found or inactive")
            validated_roles.append(role_obj)
        return validated_roles

    def _sync_user_roles(self, user_id: UUID, target_role_slugs: list[str]) -> None:
        existing_user_roles = self.session.exec(
            select(UserRole).where(UserRole.user_id == user_id)
        ).all()
        existing_by_slug = {ur.role_slug: ur for ur in existing_user_roles}
        target_set = set(target_role_slugs)

        # 1. Deactivate roles that are no longer assigned
        for slug, ur in existing_by_slug.items():
            if slug not in target_set and ur.is_active:
                ur.is_active = False
                self.session.add(ur)

        # 2. Add or re-activate roles in target_set
        for slug in target_set:
            if slug in existing_by_slug:
                ur = existing_by_slug[slug]
                if not ur.is_active:
                    ur.is_active = True
                    self.session.add(ur)
            else:
                new_ur = UserRole(user_id=user_id, role_slug=slug, is_active=True)
                self.session.add(new_ur)

        self.session.commit()

    def create(
        self, data: User, password: str, role_slugs: list[str] | None = None
    ) -> User:
        # Check unique username
        query_username = select(User).where(User.username == data.username)
        if self.session.exec(query_username).first():
            raise BadRequestException(detail="Username already registered")

        # Check unique email
        query_email = select(User).where(User.email == data.email)
        if self.session.exec(query_email).first():
            raise BadRequestException(detail="Email already registered")

        # Validate role_slugs if provided
        validated_roles = self._validate_role_slugs(role_slugs) if role_slugs else []

        # Set password hash
        data.password_hash = get_password_hash(password)

        created_user = self.repository.create(data)

        # Assign roles
        if validated_roles:
            for r in validated_roles:
                user_role = UserRole(
                    user_id=created_user.id,
                    role_slug=r.slug,
                    is_active=True,
                )
                self.session.add(user_role)
            self.session.commit()

        return self.get_by_id(created_user.id) or created_user

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

        # Handle role_slugs synchronization
        sync_roles = False
        target_role_slugs: list[str] = []
        if "role_slugs" in data_dict:
            sync_roles = True
            raw_slugs = data_dict.pop("role_slugs")
            target_role_slugs = raw_slugs if raw_slugs is not None else []
            self._validate_role_slugs(target_role_slugs)

        updated_user = self.repository.update(id, data_dict)
        if not updated_user:
            return None

        if sync_roles:
            self._sync_user_roles(updated_user.id, target_role_slugs)

        return self.get_by_id(updated_user.id)

    def assign_role(self, user_id: UUID, role_slug: str) -> User | None:
        user = self.get_by_id(user_id)
        if not user:
            return None

        self._validate_role_slugs([role_slug])

        existing = self.session.exec(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_slug == role_slug,
            )
        ).first()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                self.session.add(existing)
                self.session.commit()
        else:
            new_ur = UserRole(
                user_id=user_id,
                role_slug=role_slug,
                is_active=True,
            )
            self.session.add(new_ur)
            self.session.commit()

        return self.get_by_id(user_id)

    def remove_role(self, user_id: UUID, role_slug: str) -> User | None:
        user = self.get_by_id(user_id)
        if not user:
            return None

        existing = self.session.exec(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_slug == role_slug,
                UserRole.is_active == True,  # noqa: E712
            )
        ).first()

        if existing:
            existing.is_active = False
            self.session.add(existing)
            self.session.commit()

        return self.get_by_id(user_id)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
    ) -> int:
        filters = self._build_filters(is_active, is_superuser)
        return self.repository.count(search, extra_filters=filters)

    def get_login_history(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 50,
        is_successful: bool | None = None,
    ) -> Sequence[UserLogLogin]:
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found")

        query = select(UserLogLogin).where(UserLogLogin.user_id == user_id)
        if is_successful is not None:
            query = query.where(UserLogLogin.is_successful == is_successful)
        query = (
            query.order_by(col(UserLogLogin.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(query).all()

    def count_login_history(
        self,
        user_id: UUID,
        is_successful: bool | None = None,
    ) -> int:
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found")

        query = select(func.count(col(UserLogLogin.id))).where(
            UserLogLogin.user_id == user_id
        )
        if is_successful is not None:
            query = query.where(UserLogLogin.is_successful == is_successful)
        result = self.session.exec(query).one()
        return int(result or 0)
