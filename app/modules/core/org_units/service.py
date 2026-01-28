from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.core.org_units.models import OrgUnit
from app.modules.core.org_units.repository import OrgUnitRepository


class OrgUnitService:
    def __init__(self, session: Session):
        self.repository = OrgUnitRepository(session)

    def create(self, data: OrgUnit) -> OrgUnit:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ) -> Sequence[OrgUnit]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Optional[OrgUnit]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[OrgUnit]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: Optional[str] = None) -> int:
        return self.repository.count(search)

    def get_by_acronym_paginated(
        self,
        acronym: str,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ) -> Sequence[OrgUnit]:
        filters = self._get_acronym_filters(acronym)
        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, filters
        )

    def count_by_acronym(self, acronym: str, search: Optional[str] = None) -> int:
        filters = self._get_acronym_filters(acronym)
        return self.repository.count(search, filters)

    def get_management_units_by_acronym(
        self,
        acronym: str,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ) -> Sequence[OrgUnit]:
        filters = self._get_management_filters(acronym)
        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, filters
        )

    def count_management_units_by_acronym(
        self, acronym: str, search: Optional[str] = None
    ) -> int:
        filters = self._get_management_filters(acronym)
        return self.repository.count(search, filters)

    # --- Private Filter Methods (Ensures Consistency) ---

    def _get_acronym_filters(self, acronym: str) -> list:
        return [OrgUnit.acronym == acronym]

    def _get_management_filters(self, acronym: str) -> list:
        return [
            OrgUnit.acronym == acronym,
            OrgUnit.type == "MANAGEMENT",
        ]
