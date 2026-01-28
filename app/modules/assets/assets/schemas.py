from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FixedAssetBase(BaseModel):
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    description: str
    serial_number: Optional[str] = None
    location_detail: Optional[str] = None
    observations: Optional[str] = None
    is_saf: bool = True
    is_physically_verified: bool = False
    is_decommissioned: bool = False
    registered_at: Optional[datetime] = None
    source_files: Optional[str] = None
    group_id: UUID
    status_id: UUID
    area_id: UUID
    org_unit_id: UUID
    assigned_staff_id: Optional[UUID] = None
    custodian_staff_id: Optional[UUID] = None


class FixedAssetCreate(FixedAssetBase):
    pass


class FixedAssetUpdate(BaseModel):
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    description: Optional[str] = None
    serial_number: Optional[str] = None
    location_detail: Optional[str] = None
    observations: Optional[str] = None
    is_saf: Optional[bool] = None
    is_physically_verified: Optional[bool] = None
    is_decommissioned: Optional[bool] = None
    registered_at: Optional[datetime] = None
    source_files: Optional[str] = None
    group_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    area_id: Optional[UUID] = None
    org_unit_id: Optional[UUID] = None
    assigned_staff_id: Optional[UUID] = None
    custodian_staff_id: Optional[UUID] = None


class FixedAssetRead(FixedAssetBase):
    id: UUID
