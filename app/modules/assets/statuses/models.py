from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.assets.assets.models import FixedAsset


class AssetStatus(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_asset_status"

    name: str = Field(max_length=100, description="GOOD, REGULAR, BAD")

    # Relationships
    fixed_assets: List["FixedAsset"] = Relationship(back_populates="status")
