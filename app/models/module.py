from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from .role import RoleModule


class ModuleGroup(BaseModel, AuditMixin, table=True):
    __tablename__ = "module_groups"
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    description: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    icon: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    # Relatoinship
    modules: List["Module"] = Relationship(back_populates="group")


class Module(BaseModel, AuditMixin, table=True):
    __tablename__ = "modules"
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    icon: str | None = Field(default=None)
    route: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    # Relatoinship
    group_slug: Optional[str] = Field(default=None, foreign_key="module_groups.slug")
    group: Optional["ModuleGroup"] = Relationship(back_populates="modules")

    role_modules: List["RoleModule"] = Relationship(back_populates="module")
