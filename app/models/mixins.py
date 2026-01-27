import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import DateTime, Field, SQLModel

from app.util.datetime import get_current_time


class AuditMixin(SQLModel):
    """
    Mixin to add audit fields (created_at, updated_at, created_by_id, updated_by_id)
    to a model.
    """

    created_at: Optional[datetime] = Field(
        default_factory=get_current_time,
        sa_type=DateTime(timezone=False),  # type: ignore
        description="The timestamp when the data was created",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=False),  # type: ignore
        sa_column_kwargs={"onupdate": get_current_time},
        description="The timestamp when the data was last updated",
    )

    created_by_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="The user who created this record",
    )
    updated_by_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="The user who last updated this record",
    )
