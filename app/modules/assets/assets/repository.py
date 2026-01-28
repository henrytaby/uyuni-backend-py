from sqlmodel import Session

from app.core.repository import BaseRepository
from app.modules.assets.assets.models import FixedAsset


class FixedAssetRepository(BaseRepository[FixedAsset]):
    searchable_fields = ["name", "code_saf", "serial_number", "model"]

    def __init__(self, session: Session):
        super().__init__(session, FixedAsset)
