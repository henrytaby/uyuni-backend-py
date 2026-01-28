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
    ) -> Sequence[OrgUnit]:
        return self.repository.get_all(offset, limit, sort_by, sort_order)

    def get_by_id(self, id: UUID) -> Optional[OrgUnit]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[OrgUnit]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self) -> int:
        return self.repository.count()
