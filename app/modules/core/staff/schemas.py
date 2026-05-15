from datetime import date
from uuid import UUID

from pydantic import BaseModel


class StaffBase(BaseModel):
    external_id: int
    first_name: str
    last_name_1: str
    last_name_2: str | None = None
    full_name: str
    birth_date: date | None = None
    document_number: str
    document_location: str | None = None
    email: str | None = None
    cellphone: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str = "INCORPORADO"
    staff_type: str = "SERVIDOR PÚBLICO"
    movement_type: str | None = None
    position_id: UUID
    org_unit_id: UUID


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    external_id: int | None = None
    first_name: str | None = None
    last_name_1: str | None = None
    last_name_2: str | None = None
    full_name: str | None = None
    birth_date: date | None = None
    document_number: str | None = None
    document_location: str | None = None
    email: str | None = None
    cellphone: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str | None = None
    staff_type: str | None = None
    movement_type: str | None = None
    position_id: UUID | None = None
    org_unit_id: UUID | None = None


class StaffRead(StaffBase):
    id: UUID
