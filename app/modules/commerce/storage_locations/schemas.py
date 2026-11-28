from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.filters import (
    BaseFilterParams,
    ListQueryMixin,
    MultiStr,
    OptBool,
    OptStr,
)
from app.modules.commerce.constants import StorageLocationType


class StorageLocationFilterParams(BaseFilterParams):
    """Filtros estándar para listado y conteo de ubicaciones de almacenamiento."""

    location_type: OptStr = None
    location_types: MultiStr = None
    is_active: OptBool = None


class StorageLocationListQuery(ListQueryMixin, StorageLocationFilterParams):
    """Query params completos para listado paginado de ubicaciones."""

    sort_by: OptStr = "code"


class StorageLocationBase(BaseModel):
    code: str
    name: str
    label: str
    description: str | None = None
    is_active: bool = True


class StorageLocationCreate(StorageLocationBase):
    location_type: StorageLocationType = StorageLocationType.OTHER


class StorageLocationUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    label: str | None = None
    location_type: StorageLocationType | None = None
    description: str | None = None
    is_active: bool | None = None


class StorageLocationRead(StorageLocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_type: str = StorageLocationType.OTHER.value
