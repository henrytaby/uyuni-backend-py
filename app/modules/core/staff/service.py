from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.core.staff.models import Staff
from app.modules.core.staff.repository import StaffRepository


class StaffService:
    def __init__(self, session: Session):
        self.repository = StaffRepository(session)

    def _build_filters(
        self,
        is_active: bool | None = None,
        org_unit_id: UUID | None = None,
    ) -> list:
        filters = []
        if is_active is not None:
            filters.append(Staff.is_active == is_active)
        if org_unit_id:
            filters.append(Staff.org_unit_id == org_unit_id)
        return filters

    def create(self, data: Staff) -> Staff:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
        is_active: bool | None = None,
        org_unit_id: UUID | None = None,
    ) -> Sequence[Staff]:
        filters = self._build_filters(is_active, org_unit_id)
        return self.repository.get_all(
            offset, limit, sort_by, sort_order, search, extra_filters=filters
        )

    def get_by_id(self, id: UUID) -> Staff | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Staff | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        org_unit_id: UUID | None = None,
    ) -> int:
        filters = self._build_filters(is_active, org_unit_id)
        return self.repository.count(search, extra_filters=filters)
