from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OrgUnitBase(BaseModel):
    external_id: int
    name: str
    acronym: Optional[str] = None
    general_unit: Optional[str] = None
    type: str
    parent_id: Optional[UUID] = None


class OrgUnitCreate(OrgUnitBase):
    pass


class OrgUnitUpdate(BaseModel):
    external_id: Optional[int] = None
    name: Optional[str] = None
    acronym: Optional[str] = None
    general_unit: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[UUID] = None


class OrgUnitRead(OrgUnitBase):
    id: UUID
