import uuid

from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """
    Base model that includes common fields for all models.
    """

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,  # type: ignore[attr-defined]
        primary_key=True,
        index=True,
        description="The primary key",
    )
