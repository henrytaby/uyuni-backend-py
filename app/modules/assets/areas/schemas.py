from uuid import UUID

from pydantic import BaseModel


class AreaBase(BaseModel):
    name: str
    institution_id: UUID


class AreaCreate(AreaBase):
    pass


class AreaUpdate(BaseModel):
    name: str | None = None
    institution_id: UUID | None = None


class AreaRead(AreaBase):
    id: UUID
