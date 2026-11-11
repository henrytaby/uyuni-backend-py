from typing import TYPE_CHECKING, List

from sqlmodel import Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin

if TYPE_CHECKING:
    from app.modules.commerce.sales.models import Sale


class SalesChannel(BaseModel, AuditMixin, table=True):
    __tablename__ = "commerce_channel"

    code: str = Field(
        index=True,
        unique=True,
        max_length=50,
        description="Código o slug único (Ej: MARKETPLACE, TIKTOK_LIVE)",
    )
    name: str = Field(
        max_length=150,
        index=True,
        description="Nombre visible del canal (Ej: Marketplace, TikTok Live)",
    )
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(
        default=True, description="¿Canal activo para registrar nuevas ventas?"
    )

    # Relationships
    sales: List["Sale"] = Relationship(back_populates="sales_channel")
