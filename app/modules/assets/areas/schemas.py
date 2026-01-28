from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AreaBase(BaseModel):
    name: str
    institution_id: UUID


class AreaCreate(AreaBase):
    pass


class AreaUpdate(BaseModel):
    name: Optional[str] = None
    institution_id: Optional[UUID] = None


class AreaRead(AreaBase):
    id: UUID
