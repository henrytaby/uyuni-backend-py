from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AssetStatusBase(BaseModel):
    name: str


class AssetStatusCreate(AssetStatusBase):
    pass


class AssetStatusUpdate(BaseModel):
    name: Optional[str] = None


class AssetStatusRead(AssetStatusBase):
    id: UUID
