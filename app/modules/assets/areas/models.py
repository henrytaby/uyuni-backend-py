from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.assets.assets.models import FixedAsset
    from app.modules.assets.institutions.models import Institution


class Area(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_area"

    name: str = Field(max_length=255, description="EXPORTACIÓN")
    institution_id: UUID = Field(foreign_key="assets_institution.id")

    # Relationships
    institution: "Institution" = Relationship(back_populates="areas")
    fixed_assets: List["FixedAsset"] = Relationship(back_populates="area")
