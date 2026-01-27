from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from .module import Module
    from .user import UserRole


class RoleModule(BaseModel, AuditMixin, table=True):
    __tablename__ = "role_modules"
    __table_args__ = (
        UniqueConstraint("role_slug", "module_slug", name="uq_role_module_slugs"),
    )
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)

    can_create: bool = Field(default=False)
    # can_read: bool = Field(default=False)
    can_update: bool = Field(default=False)
    can_delete: bool = Field(default=False)
    scope_all: bool = Field(
        default=False,
        description="If True, user can see all data. If False, only own data.",
    )

    # Relatoinship
    role_slug: Optional[str] = Field(default=None, foreign_key="roles.slug")
    role: Optional["Role"] = Relationship(back_populates="role_modules")

    module_slug: Optional[str] = Field(default=None, foreign_key="modules.slug")
    module: Optional["Module"] = Relationship(back_populates="role_modules")


class Role(BaseModel, AuditMixin, table=True):
    __tablename__ = "roles"
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    icon: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)

    # Relatoinship
    role_modules: List["RoleModule"] = Relationship(back_populates="role")
    user_roles: List["UserRole"] = Relationship(back_populates="role")
