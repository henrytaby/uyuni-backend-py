from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.acts.models import Act


class ActRepository(BaseRepository[Act]):
    def __init__(self, session: Session):
        super().__init__(session, Act)
