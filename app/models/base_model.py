import uuid

import uuid6
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """
    Base model that includes common fields for all models.
    """

    id: uuid.UUID = Field(
        default_factory=uuid6.uuid7,
        primary_key=True,
        index=True,
        description="The primary key",
    )
