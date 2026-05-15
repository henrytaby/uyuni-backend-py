from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.modules.core.org_units.schemas import OrgUnitRead
from app.modules.core.positions.schemas import StaffPositionRead


class OrgUnitReadWithParent(OrgUnitRead):
    parent: Optional["OrgUnitReadWithParent"] = None
    model_config = ConfigDict(from_attributes=True)


class OrgUnitSimple(BaseModel):
    id: UUID
    name: str
    acronym: str | None = None
    parent_id: UUID | None = None
    parent: "OrgUnitSimple | None" = None


class StaffPositionSimple(BaseModel):
    id: UUID
    name: str
    level: str | None = None


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
    position_id: UUID | None = None
    org_unit_id: UUID | None = None


class StaffRead(StaffBase):
    id: UUID
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

    # Excluimos campos solicitados por el usuario para la respuesta de la API
    external_id: int = Field(exclude=True)
    phone: str | None = Field(exclude=True)
    status: str = Field(exclude=True)
    staff_type: str = Field(exclude=True)


class StaffReadDetailed(StaffRead):
    # Usamos alias internos para la lógica pero exponemos lo que pidió el usuario
    position_detail: StaffPositionRead | None = Field(None, alias="position", exclude=True)
    org_unit_detail: OrgUnitReadWithParent | None = Field(None, alias="org_unit", exclude=True)

    @computed_field
    @property
    def management_name(self) -> str | None:
        if not self.org_unit_detail:
            return None
        return (
            self.org_unit_detail.parent.name
            if self.org_unit_detail.parent
            else self.org_unit_detail.name
        )

    @computed_field
    @property
    def department_name(self) -> str | None:
        if not self.org_unit_detail or not self.org_unit_detail.parent:
            return None
        return self.org_unit_detail.name

    @computed_field
    @property
    def position_name(self) -> str | None:
        return self.position_detail.name if self.position_detail else None

    @computed_field
    @property
    def position(self) -> StaffPositionSimple | None:
        if not self.position_detail:
            return None
        return StaffPositionSimple(
            id=self.position_detail.id,
            name=self.position_detail.name,
            level=self.position_detail.level,
        )

    @computed_field
    @property
    def org_unit(self) -> OrgUnitSimple | None:
        if not self.org_unit_detail:
            return None

        def to_simple(unit) -> OrgUnitSimple | None:
            if not unit:
                return None
            return OrgUnitSimple(
                id=unit.id,
                name=unit.name,
                acronym=unit.acronym,
                parent_id=unit.parent_id,
                parent=to_simple(unit.parent),
            )

        return to_simple(self.org_unit_detail)

