from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.commerce.categories.models import Category


class CategoryRepository(BaseRepository[Category]):
    searchable_fields = ["code", "name", "description"]

    def __init__(self, session: Session):
        super().__init__(session, Category)
