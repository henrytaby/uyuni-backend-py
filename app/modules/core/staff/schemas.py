from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StaffBase(BaseModel):
    external_id: int
    first_name: str
    last_name_1: str
    last_name_2: Optional[str] = None
    full_name: str
    birth_date: Optional[date] = None
    document_number: str
    document_location: Optional[str] = None
    email: Optional[str] = None
    cellphone: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "INCORPORADO"
    staff_type: str = "SERVIDOR PÚBLICO"
    movement_type: Optional[str] = None
    position_id: UUID
    org_unit_id: UUID


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    external_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name_1: Optional[str] = None
    last_name_2: Optional[str] = None
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    document_number: Optional[str] = None
    document_location: Optional[str] = None
    email: Optional[str] = None
    cellphone: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    staff_type: Optional[str] = None
    movement_type: Optional[str] = None
    position_id: Optional[UUID] = None
    org_unit_id: Optional[UUID] = None


class StaffRead(StaffBase):
    id: UUID
