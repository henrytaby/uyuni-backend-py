import os

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "AppTransactionFastAPI"
    VERSION: str = "v1"
    PORT: int = 8000
    ENVIRONMENT: str = "local"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Security Lockout
    SECURITY_LOGIN_MAX_ATTEMPTS: int = 5
    SECURITY_LOCKOUT_MINUTES: int = 15

    # Utils
    TIME_ZONE: int
    PROJECT_ROOT: str = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # Audit
    ENABLE_ACCESS_AUDIT: bool = True
    ENABLE_DATA_AUDIT: bool = True
    
    # Log Controls
    ENABLE_ACCESS_LOGS: bool = True  # Master switch for access logging
    ACCESS_LOGS_ONLY_ERRORS: bool = False  # If True, only log 4xx/5xx responses
    
    AUDIT_EXCLUDED_PATHS: list[str] = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "GET:/health",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
