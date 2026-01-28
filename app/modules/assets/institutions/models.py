from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.assets.areas.models import Area


class Institution(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_institution"

    name: str = Field(max_length=255, description="ADUANA NACIONAL")
    code: Optional[str] = Field(default=None, max_length=50)

    # Relationships
    areas: List["Area"] = Relationship(back_populates="institution")
