from typing import Any, Mapping, Sequence
from uuid import UUID

from sqlmodel import Session

from app.core.filters import BaseFilterParams
from app.modules.commerce.storage_locations.models import StorageLocation
from app.modules.commerce.storage_locations.repository import (
    StorageLocationRepository,
)


class StorageLocationService:
    """Servicio de gestión de ubicaciones físicas de almacenamiento y exhibición."""

    def __init__(self, session: Session):
        self.session = session
        self.repository = StorageLocationRepository(session)

    def create(self, data: StorageLocation) -> StorageLocation:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> Sequence[StorageLocation]:
        return self.repository.get_all(
            offset=offset,
            limit=limit,
            sort_by=sort_by or "code",
            sort_order=sort_order,
            search=search,
            filters=filters,
        )

    def get_by_id(self, id: UUID) -> StorageLocation | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict[str, Any]) -> StorageLocation | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(
        self,
        search: str | None = None,
        filters: BaseFilterParams | Mapping[str, Any] | None = None,
    ) -> int:
        return self.repository.count(search=search, filters=filters)
