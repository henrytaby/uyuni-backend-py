from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.core.positions.models import StaffPosition


class StaffPositionRepository(BaseRepository[StaffPosition]):
    def __init__(self, session: Session):
        super().__init__(session, StaffPosition)
