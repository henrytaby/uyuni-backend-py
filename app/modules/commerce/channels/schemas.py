from uuid import UUID

from pydantic import BaseModel


class SalesChannelBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    is_active: bool = True


class SalesChannelCreate(SalesChannelBase):
    pass


class SalesChannelUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SalesChannelRead(SalesChannelBase):
    id: UUID
