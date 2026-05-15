from uuid import UUID

from pydantic import BaseModel


class OrgUnitBase(BaseModel):
    external_id: int
    name: str
    acronym: str | None = None
    general_unit: str | None = None
    type: str
    parent_id: UUID | None = None


class OrgUnitCreate(OrgUnitBase):
    pass


class OrgUnitUpdate(BaseModel):
    external_id: int | None = None
    name: str | None = None
    acronym: str | None = None
    general_unit: str | None = None
    type: str | None = None
    parent_id: UUID | None = None


class OrgUnitRead(OrgUnitBase):
    id: UUID
