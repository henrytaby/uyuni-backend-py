from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.core.staff.models import Staff


class StaffRepository(BaseRepository[Staff]):
    searchable_fields = ["full_name", "document_number", "email"]

    def __init__(self, session: Session):
        super().__init__(session, Staff)
