import re
import uuid
from datetime import datetime

from pydantic import ConfigDict, EmailStr, field_validator
from sqlmodel import Field, SQLModel

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


def _validate_username_format(v: str | None) -> str | None:
    if v is None:
        return v
    if re.search(r"\s", v):
        raise ValueError("El nombre de usuario no puede contener espacios")
    trimmed = v.strip()
    if len(trimmed) < 3:
        raise ValueError("El nombre de usuario debe contener al menos 3 caracteres")
    if len(trimmed) > 30:
        raise ValueError("El nombre de usuario no puede exceder los 30 caracteres")
    if re.search(r"^[._-]|[._-]$", trimmed):
        raise ValueError(
            "No puede iniciar ni terminar con puntos, guiones o guiones bajos"
        )
    if re.search(r"[._-]{2,}", trimmed):
        raise ValueError("No se permiten caracteres especiales (. _ -) consecutivos")
    if not USERNAME_REGEX.match(trimmed):
        raise ValueError(
            "Solo se permiten letras, números, puntos (.), "
            "guiones (-) y guiones bajos (_)"
        )
    return trimmed.lower()


class RoleSummary(SQLModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None

    model_config = ConfigDict(from_attributes=True)  # type: ignore


class UserCreate(SQLModel):
    username: str = Field(description="Unique username for login")
    email: EmailStr = Field(description="Valid email address")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    password: str = Field(
        min_length=6, description="Strong password (min 6 characters)"
    )
    phone: str | None = Field(
        default=None, max_length=30, description="Phone / WhatsApp number"
    )
    avatar_url: str | None = Field(
        default=None, max_length=500, description="Avatar image URL"
    )
    country: str | None = Field(
        default="BO", max_length=10, description="Country code (ISO)"
    )
    city: str | None = Field(default=None, max_length=100, description="City")
    address: str | None = Field(
        default=None, max_length=255, description="Physical address"
    )
    notes: str | None = Field(default=None, description="Administrative notes")
    timezone: str | None = Field(
        default="America/La_Paz", max_length=50, description="IANA Timezone"
    )
    is_active: bool = Field(default=True, description="Whether the user is active")
    is_superuser: bool = Field(
        default=False, description="Whether the user has superuser privileges"
    )
    is_verified: bool = Field(
        default=False, description="Whether the user email is verified"
    )
    role_slugs: list[str] = Field(
        default_factory=list, description="Role slugs to assign to the user"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        res = _validate_username_format(v)
        if res is None:
            raise ValueError("El nombre de usuario es obligatorio")
        return res

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    @field_validator(
        "first_name",
        "last_name",
        "phone",
        "avatar_url",
        "city",
        "address",
        "country",
        "timezone",
        "notes",
    )
    @classmethod
    def clean_strings(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class UserUpdate(SQLModel):
    username: str | None = Field(default=None, description="Unique username for login")
    email: EmailStr | None = Field(default=None, description="Valid email address")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    password: str | None = Field(default=None, description="New strong password")
    phone: str | None = Field(
        default=None, max_length=30, description="Phone / WhatsApp number"
    )
    avatar_url: str | None = Field(
        default=None, max_length=500, description="Avatar image URL"
    )
    country: str | None = Field(
        default=None, max_length=10, description="Country code (ISO)"
    )
    city: str | None = Field(default=None, max_length=100, description="City")
    address: str | None = Field(
        default=None, max_length=255, description="Physical address"
    )
    notes: str | None = Field(default=None, description="Administrative notes")
    timezone: str | None = Field(
        default=None, max_length=50, description="IANA Timezone"
    )
    is_active: bool | None = Field(
        default=None, description="Whether the user is active"
    )
    is_superuser: bool | None = Field(
        default=None, description="Whether the user has superuser privileges"
    )
    is_verified: bool | None = Field(
        default=None, description="Whether the user email is verified"
    )
    role_slugs: list[str] | None = Field(
        default=None, description="Role slugs to assign (replaces existing if provided)"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        return _validate_username_format(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: EmailStr | None) -> str | None:
        if v is None:
            return None
        return str(v).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None and v != "":
            if len(v) < 6:
                raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v

    @field_validator(
        "first_name",
        "last_name",
        "phone",
        "avatar_url",
        "city",
        "address",
        "country",
        "timezone",
        "notes",
    )
    @classmethod
    def clean_strings(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class UserRead(SQLModel):
    id: uuid.UUID
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    country: str | None = "BO"
    city: str | None = None
    address: str | None = None
    notes: str | None = None
    timezone: str | None = "America/La_Paz"
    is_verified: bool
    is_active: bool
    is_superuser: bool
    role_slugs: list[str] = Field(default_factory=list)
    roles: list[RoleSummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)  # type: ignore


class UserReadDetailed(UserRead):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)  # type: ignore


class UserLogLoginRead(SQLModel):
    id: uuid.UUID
    created_at: datetime | None = None
    ip_address: str
    host_info: str
    is_successful: bool
    logged_out_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)  # type: ignore
