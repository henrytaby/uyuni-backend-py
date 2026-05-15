from uuid import UUID

from pydantic import BaseModel


class InstitutionBase(BaseModel):
    name: str
    code: str | None = None


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


class InstitutionRead(InstitutionBase):
    id: UUID
