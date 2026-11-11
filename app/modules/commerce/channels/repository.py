from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.commerce.channels.models import SalesChannel


class SalesChannelRepository(BaseRepository[SalesChannel]):
    searchable_fields = ["code", "name", "description"]

    def __init__(self, session: Session):
        super().__init__(session, SalesChannel)
