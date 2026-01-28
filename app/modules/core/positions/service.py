from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.core.positions.models import StaffPosition
from app.modules.core.positions.repository import StaffPositionRepository


class StaffPositionService:
    def __init__(self, session: Session):
        self.repository = StaffPositionRepository(session)

    def create(self, data: StaffPosition) -> StaffPosition:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Sequence[StaffPosition]:
        return self.repository.get_all(offset, limit, sort_by, sort_order)

    def get_by_id(self, id: UUID) -> Optional[StaffPosition]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[StaffPosition]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self) -> int:
        return self.repository.count()
