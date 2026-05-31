from sqlmodel import Session

from app.core.repository import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    searchable_fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, session: Session):
        super().__init__(session, User)
