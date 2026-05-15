from uuid import UUID

from pydantic import BaseModel


class AssetGroupBase(BaseModel):
    name: str


class AssetGroupCreate(AssetGroupBase):
    pass


class AssetGroupUpdate(BaseModel):
    name: str | None = None


class AssetGroupRead(AssetGroupBase):
    id: UUID
