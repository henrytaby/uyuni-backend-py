from uuid import UUID

from pydantic import BaseModel


class StaffPositionBase(BaseModel):
    external_id: int
    name: str
    level: str | None = None
    position_type: str | None = None


class StaffPositionCreate(StaffPositionBase):
    pass


class StaffPositionUpdate(BaseModel):
    external_id: int | None = None
    name: str | None = None
    level: str | None = None
    position_type: str | None = None


class StaffPositionRead(StaffPositionBase):
    id: UUID
