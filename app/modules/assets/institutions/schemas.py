from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class InstitutionBase(BaseModel):
    name: str
    code: Optional[str] = None


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class InstitutionRead(InstitutionBase):
    id: UUID
