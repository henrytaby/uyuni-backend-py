from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.assets.institutions.models import Institution
from app.modules.assets.institutions.repository import InstitutionRepository


class InstitutionService:
    def __init__(self, session: Session):
        self.repository = InstitutionRepository(session)

    def create(self, data: Institution) -> Institution:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ) -> Sequence[Institution]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Optional[Institution]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[Institution]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: Optional[str] = None) -> int:
        return self.repository.count(search)
