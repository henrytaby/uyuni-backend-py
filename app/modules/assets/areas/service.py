from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.assets.areas.models import Area
from app.modules.assets.areas.repository import AreaRepository


class AreaService:
    def __init__(self, session: Session):
        self.repository = AreaRepository(session)

    def create(self, data: Area) -> Area:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
    ) -> Sequence[Area]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Optional[Area]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[Area]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: Optional[str] = None) -> int:
        return self.repository.count(search)
