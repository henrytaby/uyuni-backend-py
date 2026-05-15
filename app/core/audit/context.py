import uuid
from contextvars import ContextVar

from fastapi import Request

# ContextVar to store current user_id for logging/CDC
audit_user_id_cv: ContextVar[uuid.UUID | None] = ContextVar(
    "audit_user_id", default=None
)
# ContextVar to store current username
audit_username_cv: ContextVar[str | None] = ContextVar(
    "audit_username", default=None
)
# ContextVar to store current IP address
audit_ip_address_cv: ContextVar[str | None] = ContextVar(
    "audit_ip_address", default=None
)
# ContextVar to store current user_agent
audit_user_agent_cv: ContextVar[str | None] = ContextVar(
    "audit_user_agent", default=None
)


def set_audit_context(
    user_id: uuid.UUID | int | None,
    ip_address: str | None,
    username: str | None = None,
    user_agent: str | None = None,
):
    """Set context variables for the current request"""
    # Normalize to UUID if possible or keep as is?
    # Mypy complained: incompatible type "UUID | None"; expected "int | None".
    # If I change type hint to Union it fixes it.
    audit_user_id_cv.set(user_id)  # type: ignore
    audit_ip_address_cv.set(ip_address)
    audit_username_cv.set(username)
    audit_user_agent_cv.set(user_agent)


def get_audit_user_id() -> uuid.UUID | None:
    return audit_user_id_cv.get()


def get_audit_ip_address() -> str | None:
    return audit_ip_address_cv.get()


def get_audit_username() -> str | None:
    return audit_username_cv.get()


def get_audit_user_agent() -> str | None:
    return audit_user_agent_cv.get()


async def skip_access_audit(request: Request):
    """
    Dependency to skip access audit for specific endpoints.
    Usage: @router.get("/", dependencies=[Depends(skip_access_audit)])
    """
    request.state.skip_audit = True
