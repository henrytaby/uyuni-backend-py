import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field

from app.models.base_model import BaseModel
from app.util.datetime import get_current_time


class AuditLog(BaseModel, table=True):
    __tablename__ = "audit_logs"

    # id inherited from BaseModel (UUID)
    user_id: uuid.UUID | None = Field(default=None, index=True)
    username: str | None = Field(default=None)
    action: str = Field(index=True)  # CREATE, READ, UPDATE, DELETE, ACCESS
    entity_type: str = Field(index=True)  # Product, User, Endpoint
    entity_id: str | None = Field(default=None, index=True)
    changes: Any | None = Field(default=None, sa_column=Column(JSON))
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    timestamp: datetime = Field(
        default_factory=get_current_time,
        sa_column=Column(DateTime(timezone=False), index=True),
    )
