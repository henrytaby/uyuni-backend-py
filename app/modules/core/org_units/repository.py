from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.core.org_units.models import OrgUnit


class OrgUnitRepository(BaseRepository[OrgUnit]):
    def __init__(self, session: Session):
        super().__init__(session, OrgUnit)
