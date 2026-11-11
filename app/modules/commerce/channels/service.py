from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.commerce.channels.models import SalesChannel
from app.modules.commerce.channels.repository import SalesChannelRepository


class SalesChannelService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = SalesChannelRepository(session)

    def create(self, data: SalesChannel) -> SalesChannel:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> Sequence[SalesChannel]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> SalesChannel | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> SalesChannel | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)
