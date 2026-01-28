from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.assets.assets.models import FixedAsset


class AssetGroup(BaseModel, AuditMixin, table=True):
    __tablename__ = "assets_asset_group"

    name: str = Field(max_length=255, description="CATRE, PC, etc")

    # Relationships
    fixed_assets: List["FixedAsset"] = Relationship(back_populates="group")
