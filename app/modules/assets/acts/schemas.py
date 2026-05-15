from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ActBase(BaseModel):
    act_number: str
    registered_at: datetime | None = None
    pdf_attachment: str | None = None
    staff_id: UUID | None = None


class ActCreate(ActBase):
    pass


class ActUpdate(BaseModel):
    act_number: str | None = None
    registered_at: datetime | None = None
    pdf_attachment: str | None = None
    staff_id: UUID | None = None


class ActRead(ActBase):
    id: UUID
