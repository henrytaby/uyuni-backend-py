from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.assets.assets.models import FixedAsset


class AssetActLink(SQLModel, table=True):
    __tablename__ = "assets_asset_act_link"

    asset_id: UUID = Field(foreign_key="assets_fixed_asset.id", primary_key=True)
    act_id: UUID = Field(foreign_key="assets_act.id", primary_key=True)


class Act(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_act"

    act_number: str = Field(index=True, unique=True, max_length=100)
    registered_at: Optional[datetime] = Field(default=None)
    pdf_attachment: Optional[str] = Field(default=None, max_length=500)

    staff_id: Optional[UUID] = Field(default=None, foreign_key="core_staff.id")

    # Relationships
    fixed_assets: List["FixedAsset"] = Relationship(
        back_populates="acts", link_model=AssetActLink
    )
