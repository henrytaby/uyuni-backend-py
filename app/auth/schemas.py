from typing import List, Optional

from sqlmodel import Field, SQLModel


class UserCreate(SQLModel):
    username: str = Field(index=True, unique=True, description="Unique username for login")
    email: str = Field(index=True, unique=True, description="Valid email address")
    first_name: Optional[str] = Field(default=None, description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    password: str = Field(description="Strong password (will be hashed)")
    model_config = {"extra": "forbid"}


class User(SQLModel):
    id: int
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    is_verified: bool = Field(default=False)
    password_hash: str
    model_config = {"extra": "forbid"}


class UserResponse(SQLModel):
    id: int = Field(description="User unique identifier")
    username: str = Field(description="Unique username")
    email: str = Field(description="User email")
    first_name: Optional[str] = Field(default=None, description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    is_verified: bool = Field(default=False, description="Whether the email is verified")
    model_config = {"extra": "forbid"}


class Token(SQLModel):
    access_token: str = Field(description="JWT Access Token for API access")
    token_type: str = Field(description="Token type, usually 'bearer'")
    refresh_token: str = Field(description="Token to refresh the access token")


class TokenData(SQLModel):
    username: Optional[str] = None


class LogoutRequest(SQLModel):
    refresh_token: str = Field(description="Refresh token to revoke")


# --- RBAC SCHEMAS ---


class RoleInfo(SQLModel):
    id: int
    name: str
    icon: Optional[str] = None


class UserModulePermission(SQLModel):
    module_slug: str
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_read: bool = False  # Derived/Implicit permission


class ModuleMenu(SQLModel):
    name: str
    slug: str
    route: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    permissions: UserModulePermission


class ModuleGroupMenu(SQLModel):
    group_name: str
    slug: str
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    modules: List[ModuleMenu]
