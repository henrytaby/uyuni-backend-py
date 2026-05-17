from app.core.catalogs.base import CatalogProvider
from app.core.exceptions import NotFoundException


class CatalogRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, CatalogProvider] = {}

    def register(self, key: str, provider: CatalogProvider) -> None:
        self._providers[key] = provider

    def get_provider(self, key: str) -> CatalogProvider:
        if key not in self._providers:
            raise NotFoundException(detail=f"Catalog '{key}' not found")
        return self._providers[key]


global_registry = CatalogRegistry()
