import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship

from app.models.base_model import BaseModel
from app.models.mixins import AuditMixin
from app.util.datetime import get_current_time

if TYPE_CHECKING:
    from .role import Role


class User(BaseModel, AuditMixin, table=True):
    __tablename__ = "users"
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    password_hash: str = Field(exclude=True)

    # Security & Analytics
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    last_login_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    # Relationship
    user_roles: List["UserRole"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserRole.user_id"},
    )


class UserRole(BaseModel, AuditMixin, table=True):
    __tablename__ = "user_roles"
    is_active: bool = Field(default=True)

    # Relationship
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(
        back_populates="user_roles",
        sa_relationship_kwargs={"foreign_keys": "[UserRole.user_id]"},
    )

    role_slug: Optional[str] = Field(default=None, foreign_key="roles.slug")
    role: Optional["Role"] = Relationship(back_populates="user_roles")


class UserRevokedToken(BaseModel, table=True):
    __tablename__ = "user_revoked_tokens"
    token: str = Field(index=True, unique=True)
    user_id: uuid.UUID = Field(index=True)
    revoked_at: Optional[datetime] = Field(
        default_factory=get_current_time,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="The timestamp when the token was Revoked",
    )


class UserLogLogin(BaseModel, table=True):
    __tablename__ = "user_log_logins"
    created_at: Optional[datetime] = Field(
        default_factory=get_current_time,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="The timestamp when the log was created",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=False), onupdate=get_current_time, nullable=True
        ),
        description="The timestamp when the log was last updated",
    )
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    username: Optional[str] = Field(
        description="The username used in the login attempt", default=None
    )
    # Security: Password field removed to prevent logging sensitive data

    token: Optional[str] = Field(description="The generated token", default=None)
    token_expiration: Optional[datetime] = Field(
        description="The expiration date and time of the token", default=None
    )
    ip_address: str = Field(
        description="The IP address from where the user is authenticating"
    )
    host_info: str = Field(description="Host information")
    logged_out_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="The timestamp when the user logged out",
    )
    is_successful: bool = Field(
        description="Indicates if the login attempt was successful"
    )
