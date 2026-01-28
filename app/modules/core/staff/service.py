from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.core.staff.models import Staff
from app.modules.core.staff.repository import StaffRepository


class StaffService:
    def __init__(self, session: Session):
        self.repository = StaffRepository(session)

    def create(self, data: Staff) -> Staff:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        query: Optional[str] = None,
    ) -> Sequence[Staff]:
        if query:
            return self.repository.search(query, offset, limit, sort_by, sort_order)
        return self.repository.get_all(offset, limit, sort_by, sort_order)

    def get_by_id(self, id: UUID) -> Optional[Staff]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[Staff]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self) -> int:
        return self.repository.count()
