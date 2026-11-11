from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.commerce.live_baskets.models import LiveBasket


class LiveBasketRepository(BaseRepository[LiveBasket]):
    searchable_fields = ["code", "name", "label", "target_audience"]

    def __init__(self, session: Session):
        super().__init__(session, LiveBasket)
