from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.institutions.models import Institution


class InstitutionRepository(BaseRepository[Institution]):
    searchable_fields = ["name", "acronym"]

    def __init__(self, session: Session):
        super().__init__(session, Institution)
