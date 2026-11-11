from typing import Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.commerce.live_baskets.models import LiveBasket
from app.modules.commerce.live_baskets.repository import LiveBasketRepository


class LiveBasketService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = LiveBasketRepository(session)

    def create(self, data: LiveBasket) -> LiveBasket:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> Sequence[LiveBasket]:
        return self.repository.get_all(offset, limit, sort_by, sort_order, search)

    def get_by_id(self, id: UUID) -> LiveBasket | None:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> LiveBasket | None:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self, search: str | None = None) -> int:
        return self.repository.count(search)
