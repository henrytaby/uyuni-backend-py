from sqlmodel import Session

from app.core.filters import FilterOp, FilterSpec
from app.core.repository import BaseRepository
from app.modules.commerce.storage_locations.models import StorageLocation


class StorageLocationRepository(BaseRepository[StorageLocation]):
    searchable_fields = ["code", "name", "label", "description"]
    filter_fields = {
        "location_type": FilterOp.EQ,
        "location_types": FilterSpec("location_type", FilterOp.IN),
        "is_active": FilterOp.EQ,
    }

    def __init__(self, session: Session):
        super().__init__(session, StorageLocation)
