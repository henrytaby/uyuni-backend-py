from typing import Any, Optional

from pydantic import BaseModel


class CatalogItemSchema(BaseModel):
    value: Any
    label: str
    extra: Optional[dict] = None
