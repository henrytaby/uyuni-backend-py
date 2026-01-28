from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StaffPositionBase(BaseModel):
    external_id: int
    name: str
    level: Optional[str] = None
    position_type: Optional[str] = None


class StaffPositionCreate(StaffPositionBase):
    pass


class StaffPositionUpdate(BaseModel):
    external_id: Optional[int] = None
    name: Optional[str] = None
    level: Optional[str] = None
    position_type: Optional[str] = None


class StaffPositionRead(StaffPositionBase):
    id: UUID
