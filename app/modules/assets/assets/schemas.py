from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FixedAssetBase(BaseModel):
    old_code: str | None = None
    new_code: str | None = None
    description: str
    serial_number: str | None = None
    location_detail: str | None = None
    observations: str | None = None
    is_saf: bool = True
    is_physically_verified: bool = False
    is_decommissioned: bool = False
    registered_at: datetime | None = None
    source_files: str | None = None
    group_id: UUID
    status_id: UUID
    area_id: UUID
    org_unit_id: UUID
    assigned_staff_id: UUID | None = None
    custodian_staff_id: UUID | None = None


class FixedAssetCreate(FixedAssetBase):
    pass


class FixedAssetUpdate(BaseModel):
    old_code: str | None = None
    new_code: str | None = None
    description: str | None = None
    serial_number: str | None = None
    location_detail: str | None = None
    observations: str | None = None
    is_saf: bool | None = None
    is_physically_verified: bool | None = None
    is_decommissioned: bool | None = None
    registered_at: datetime | None = None
    source_files: str | None = None
    group_id: UUID | None = None
    status_id: UUID | None = None
    area_id: UUID | None = None
    org_unit_id: UUID | None = None
    assigned_staff_id: UUID | None = None
    custodian_staff_id: UUID | None = None


class FixedAssetRead(FixedAssetBase):
    id: UUID
