from typing import Optional, Sequence

from sqlmodel import Session, col, or_, select

from app.core.repository import BaseRepository
from app.modules.core.staff.models import Staff


class StaffRepository(BaseRepository[Staff]):
    def __init__(self, session: Session):
        super().__init__(session, Staff)

    def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Sequence[Staff]:
        statement = select(self.model)
        if query:
            statement = statement.where(
                or_(
                    col(Staff.full_name).ilike(f"%{query}%"),
                    col(Staff.document_number).ilike(f"%{query}%"),
                    col(Staff.email).ilike(f"%{query}%"),
                )
            )

        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())

        statement = statement.offset(offset).limit(limit)
        return self.session.exec(statement).all()
