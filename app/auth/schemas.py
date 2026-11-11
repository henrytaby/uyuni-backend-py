import uuid
from datetime import datetime

from pydantic import ConfigDict, EmailStr, field_validator
from sqlmodel import Field, SQLModel

from app.modules.core.users.schemas import _validate_username_format


class UserCreate(SQLModel):
    username: str = Field(
        index=True, unique=True, description="Unique username for login"
    )
    email: EmailStr = Field(index=True, unique=True, description="Valid email address")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    password: str = Field(min_length=6, description="Strong password (will be hashed)")
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

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class User(SQLModel):
    id: uuid.UUID
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    is_verified: bool = Field(default=False)
    password_hash: str
    model_config = ConfigDict(extra="forbid", from_attributes=True)  # type: ignore


class UserResponse(SQLModel):
    id: uuid.UUID = Field(description="User unique identifier")
    username: str = Field(description="Unique username")
    email: str = Field(description="User email")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    phone: str | None = Field(default=None, description="Phone number / WhatsApp")
    avatar_url: str | None = Field(default=None, description="Avatar image URL")
    country: str | None = Field(default="BO", description="Country ISO code")
    city: str | None = Field(default=None, description="City or branch")
    address: str | None = Field(default=None, description="Physical address")
    timezone: str | None = Field(
        default="America/La_Paz", description="Timezone (IANA)"
    )
    is_verified: bool = Field(
        default=False, description="Whether the email is verified"
    )
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    model_config = ConfigDict(extra="ignore", from_attributes=True)  # type: ignore


class UserProfileUpdate(SQLModel):
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    phone: str | None = Field(
        default=None, max_length=30, description="Phone number / WhatsApp"
    )
    avatar_url: str | None = Field(
        default=None, max_length=500, description="Avatar image URL"
    )
    country: str | None = Field(
        default=None, max_length=10, description="Country code (ISO)"
    )
    city: str | None = Field(default=None, max_length=100, description="City or branch")
    address: str | None = Field(
        default=None, max_length=255, description="Physical address"
    )
    timezone: str | None = Field(
        default=None, max_length=50, description="Timezone (IANA)"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore

    @field_validator(
        "first_name",
        "last_name",
        "phone",
        "city",
        "address",
        "country",
        "timezone",
    )
    @classmethod
    def clean_strings(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class UserChangePassword(SQLModel):
    current_password: str = Field(min_length=1, description="Current password")
    new_password: str = Field(
        min_length=6, description="New strong password (min 6 characters)"
    )
    model_config = ConfigDict(extra="forbid")  # type: ignore

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres")
        return v


class Token(SQLModel):
    access_token: str = Field(description="JWT Access Token for API access")
    token_type: str = Field(description="Token type, usually 'bearer'")
    refresh_token: str = Field(description="Token to refresh the access token")


class TokenData(SQLModel):
    username: str | None = None


class LogoutRequest(SQLModel):
    refresh_token: str = Field(description="Refresh token to revoke")


# --- RBAC SCHEMAS ---


class RoleInfo(SQLModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    model_config = ConfigDict(from_attributes=True)  # type: ignore


class UserModulePermission(SQLModel):
    module_slug: str
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_read: bool = False  # Derived/Implicit permission
    scope_all: bool = Field(
        default=False, description="If True, can access all records. Else, own records."
    )


class ModuleMenu(SQLModel):
    name: str
    slug: str
    route: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    permissions: UserModulePermission


class ModuleGroupMenu(SQLModel):
    group_name: str
    slug: str
    icon: str | None = None
    sort_order: int | None = None
    modules: list[ModuleMenu]
