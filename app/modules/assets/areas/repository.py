from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.areas.models import Area


class AreaRepository(BaseRepository[Area]):
    def __init__(self, session: Session):
        super().__init__(session, Area)
