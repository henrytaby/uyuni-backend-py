from typing import Sequence
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
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> Sequence[Area]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Area | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Area | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)
