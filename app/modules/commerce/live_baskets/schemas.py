from uuid import UUID

from pydantic import BaseModel


class LiveBasketBase(BaseModel):
    code: str
    name: str
    label: str
    description: str | None = None
    price_range: str | None = None
    target_audience: str | None = None


class LiveBasketCreate(LiveBasketBase):
    pass


class LiveBasketUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    label: str | None = None
    description: str | None = None
    price_range: str | None = None
    target_audience: str | None = None


class LiveBasketRead(LiveBasketBase):
    id: UUID
