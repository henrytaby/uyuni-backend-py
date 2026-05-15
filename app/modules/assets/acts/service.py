from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.assets.acts.models import Act
from app.modules.assets.acts.repository import ActRepository


class ActService:
    def __init__(self, session: Session):
        self.repository = ActRepository(session)

    def create(self, data: Act) -> Act:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> Sequence[Act]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> Act | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Act | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)
