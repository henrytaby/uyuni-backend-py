import uuid
from typing import Any, Optional, Sequence

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.core.org_units.models import OrgUnit
from app.modules.core.staff.models import Staff


class StaffRepository(BaseRepository[Staff]):
    searchable_fields = ["full_name", "document_number", "email","cellphone"]

    def __init__(self, session: Session):
        super().__init__(session, Staff)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        extra_filters: Optional[list[Any]] = None,
    ) -> Sequence[Staff]:
        statement = select(self.model).options(
            selectinload(Staff.position),
            selectinload(Staff.org_unit).selectinload(OrgUnit.parent),
        )
        statement = self._apply_search(statement, search)

        if extra_filters:
            statement = statement.where(*extra_filters)

        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                statement = statement.order_by(column.desc())
            else:
                statement = statement.order_by(column.asc())

        statement = statement.offset(offset).limit(limit)
        return self.session.exec(statement).all()  # type: ignore[no-any-return]

    def get_by_id(self, id: uuid.UUID | int) -> Optional[Staff]:
        statement = select(Staff).where(Staff.id == id).options(
            selectinload(Staff.position),
            selectinload(Staff.org_unit).selectinload(OrgUnit.parent),
        )
        return self.session.exec(statement).first()
