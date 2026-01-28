from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.core.staff.models import Staff


class StaffPosition(BaseModel, AuditMixin, table=True):
    __tablename__ = "core_staff_position"

    external_id: int = Field(index=True, description="Original system item number")
    name: str = Field(max_length=255)
    level: Optional[str] = Field(default=None, max_length=50)
    position_type: Optional[str] = Field(default=None, max_length=100)

    # Relationships
    staff: List["Staff"] = Relationship(back_populates="position")
