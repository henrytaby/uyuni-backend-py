import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.core.org_units.models import OrgUnit
    from app.modules.core.positions.models import StaffPosition


class Staff(BaseModel, AuditMixin, table=True):
    __tablename__ = "core_staff"

    external_id: int = Field(index=True, unique=True, description="Orig. system ID")
    first_name: str = Field(max_length=100)
    last_name_1: str = Field(max_length=100)
    last_name_2: Optional[str] = Field(default=None, max_length=100)
    full_name: str = Field(max_length=255)

    birth_date: Optional[date] = None
    document_number: str = Field(index=True, unique=True, max_length=20)
    document_location: Optional[str] = Field(default=None, max_length=50)

    email: Optional[str] = Field(default=None, max_length=255)
    cellphone: Optional[str] = Field(default=None, max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=500)

    status: str = Field(default="INCORPORADO")
    staff_type: str = Field(default="SERVIDOR PÚBLICO")
    movement_type: Optional[str] = Field(default=None, max_length=100)

    position_id: uuid.UUID = Field(foreign_key="core_staff_position.id")
    org_unit_id: uuid.UUID = Field(foreign_key="core_org_unit.id")

    # Relationships
    org_unit: "OrgUnit" = Relationship(back_populates="staff")
    position: "StaffPosition" = Relationship(back_populates="staff")
