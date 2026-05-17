from typing import Protocol

from sqlmodel import Session

from app.core.catalogs.schemas import CatalogItemSchema


class CatalogProvider(Protocol):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        """Hace la consulta a la BD y formatea el resultado en CatalogItemSchema."""
        ...
