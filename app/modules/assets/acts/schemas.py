from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ActBase(BaseModel):
    act_number: str
    registered_at: Optional[datetime] = None
    pdf_attachment: Optional[str] = None
    staff_id: Optional[UUID] = None


class ActCreate(ActBase):
    pass


class ActUpdate(BaseModel):
    act_number: Optional[str] = None
    registered_at: Optional[datetime] = None
    pdf_attachment: Optional[str] = None
    staff_id: Optional[UUID] = None


class ActRead(ActBase):
    id: UUID
