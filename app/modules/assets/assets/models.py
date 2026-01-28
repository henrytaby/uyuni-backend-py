from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin
from app.modules.assets.acts.models import AssetActLink

if TYPE_CHECKING:
    from app.modules.assets.acts.models import Act
    from app.modules.assets.areas.models import Area
    from app.modules.assets.groups.models import AssetGroup
    from app.modules.assets.statuses.models import AssetStatus


class FixedAsset(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_fixed_asset"

    old_code: Optional[str] = Field(default=None, index=True, max_length=100)
    new_code: Optional[str] = Field(default=None, index=True, max_length=100)
    description: str = Field(max_length=1000)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    location_detail: Optional[str] = Field(default=None, max_length=500)
    observations: Optional[str] = Field(default=None, max_length=1000)

    is_saf: bool = Field(default=True)
    is_physically_verified: bool = Field(default=False)
    is_decommissioned: bool = Field(default=False)

    registered_at: Optional[datetime] = Field(default=None)
    source_files: Optional[str] = Field(default=None, max_length=500)

    # Foreign Keys
    group_id: UUID = Field(foreign_key="assets_asset_group.id")
    status_id: UUID = Field(foreign_key="assets_asset_status.id")
    area_id: UUID = Field(foreign_key="assets_area.id")
    org_unit_id: UUID = Field(foreign_key="core_org_unit.id")

    assigned_staff_id: Optional[UUID] = Field(default=None, foreign_key="core_staff.id")
    custodian_staff_id: Optional[UUID] = Field(
        default=None, foreign_key="core_staff.id"
    )

    # Relationships
    group: "AssetGroup" = Relationship(back_populates="fixed_assets")
    status: "AssetStatus" = Relationship(back_populates="fixed_assets")
    area: "Area" = Relationship(back_populates="fixed_assets")

    # Acts relationship (M2M)
    acts: List["Act"] = Relationship(
        back_populates="fixed_assets", link_model=AssetActLink
    )
