from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.statuses.models import AssetStatus


class AssetStatusRepository(BaseRepository[AssetStatus]):
    searchable_fields = ["name"]

    def __init__(self, session: Session):
        super().__init__(session, AssetStatus)
