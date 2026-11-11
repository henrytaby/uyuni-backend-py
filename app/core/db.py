import json
import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# from ..models.module import Module, ModuleGroup
# from ..models.role import Role, RoleModule
# from ..models.user import User, UserRole, UserRevokedToken

"""
Docs about this implementation
https://fastapi.tiangolo.com/tutorial/sql-databases/#run-the-app

WARNING: create_db_and_tables() uses SQLModel.metadata.create_all() which is
suitable for development and testing. For production deployments, use Alembic
migrations to manage database schema changes safely.
"""


def json_serializer(obj: Any) -> str:
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return json.dumps(obj, ensure_ascii=False)


# Configuración de Engine optimizada para Cloud / Serverless (Neon, PostgreSQL)
engine_kwargs: dict[str, Any] = {
    "echo": False,
    "json_serializer": json_serializer,
    # pool_pre_ping prueba la conexión antes de usarla; si Neon cerró el SSL por
    # inactividad, reconecta transparentemente sin lanzar OperationalError.
    "pool_pre_ping": True,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    # Recicla conexiones cada 5 min para evitar timeouts de SSL/PgBouncer
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine: Engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
