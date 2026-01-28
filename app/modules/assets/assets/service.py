from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import Session

from app.modules.assets.assets.models import FixedAsset
from app.modules.assets.assets.repository import FixedAssetRepository


class FixedAssetService:
    def __init__(self, session: Session):
        self.repository = FixedAssetRepository(session)

    def create(self, data: FixedAsset) -> FixedAsset:
        return self.repository.create(data)

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Sequence[FixedAsset]:
        return self.repository.get_all(offset, limit, sort_by, sort_order)

    def get_by_id(self, id: UUID) -> Optional[FixedAsset]:
        return self.repository.get_by_id(id)

    def update(self, id: UUID, data: dict) -> Optional[FixedAsset]:
        return self.repository.update(id, data)

    def delete(self, id: UUID) -> bool:
        return self.repository.delete(id)

    def count(self) -> int:
        return self.repository.count()
