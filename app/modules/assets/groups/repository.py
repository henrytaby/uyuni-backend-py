from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.groups.models import AssetGroup


class AssetGroupRepository(BaseRepository[AssetGroup]):
    def __init__(self, session: Session):
        super().__init__(session, AssetGroup)
