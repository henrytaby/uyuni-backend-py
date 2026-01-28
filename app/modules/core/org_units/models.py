from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.core.staff.models import Staff


class OrgUnit(BaseModel, AuditMixin, table=True):
    __tablename__ = "core_org_unit"

    external_id: int = Field(index=True, unique=True, description="Orig. system code")
    name: str = Field(max_length=255)
    acronym: Optional[str] = Field(default=None, max_length=50)
    general_unit: Optional[str] = Field(default=None, max_length=10)
    type: str = Field(description="MANAGEMENT / DEPARTMENT")

    parent_id: Optional[UUID] = Field(default=None, foreign_key="core_org_unit.id")

    # Relationships
    staff: List["Staff"] = Relationship(back_populates="org_unit")
    children: List["OrgUnit"] = Relationship(back_populates="parent")
    parent: Optional["OrgUnit"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "OrgUnit.id"}
    )
