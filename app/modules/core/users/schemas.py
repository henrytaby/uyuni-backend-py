import uuid
from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class UserCreate(SQLModel):
    username: str = Field(description="Unique username for login")
    email: str = Field(description="Valid email address")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    password: str = Field(description="Strong password")
    is_active: bool = Field(default=True, description="Whether the user is active")
    is_superuser: bool = Field(
        default=False, description="Whether the user has superuser privileges"
    )
    is_verified: bool = Field(
        default=False, description="Whether the user email is verified"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore


class UserUpdate(SQLModel):
    username: str | None = Field(default=None, description="Unique username for login")
    email: str | None = Field(default=None, description="Valid email address")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    password: str | None = Field(default=None, description="New strong password")
    is_active: bool | None = Field(
        default=None, description="Whether the user is active"
    )
    is_superuser: bool | None = Field(
        default=None, description="Whether the user has superuser privileges"
    )
    is_verified: bool | None = Field(
        default=None, description="Whether the user email is verified"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore


class UserRead(SQLModel):
    id: uuid.UUID
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_verified: bool
    is_active: bool
    is_superuser: bool

    model_config = ConfigDict(from_attributes=True)  # type: ignore


class UserReadDetailed(UserRead):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)  # type: ignore

