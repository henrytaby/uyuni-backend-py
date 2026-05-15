import uuid

import structlog
from fastapi import Request
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.utils import decode_token
from app.core.config import settings
from app.models.audit import AuditLog

from .context import set_audit_context

logger = structlog.get_logger("audit.middleware")


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs access events to the audit_logs table.

    The SQLAlchemy engine is resolved at runtime via ``request.app.state.engine``,
    which is the standard FastAPI pattern for sharing application state across
    middleware and endpoints. The engine is assigned during the application
    lifespan (see ``main.py``) and can be swapped in tests by setting
    ``app.state.engine = test_engine``.
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Check Global Disable
        if not settings.ENABLE_ACCESS_AUDIT:
            return await call_next(request)

        path = request.url.path
        method = request.method
        for excluded in settings.AUDIT_EXCLUDED_PATHS:
            # Case 1: "METHOD:/path"
            if ":" in excluded:
                ex_method, ex_path = excluded.split(":", 1)
                if method.upper() == ex_method.upper() and path.startswith(ex_path):
                    return await call_next(request)
            # Case 2: "/path" (All methods)
            elif path.startswith(excluded):
                # Special handling for root "/" to avoid matching everything
                if excluded == "/":
                    if path == "/":
                        return await call_next(request)
                else:
                    return await call_next(request)

        # 2. Extract User ID from Token (Manual decode to avoid interfering
        # with Auth Dependencies)
        user_id: uuid.UUID | None = None
        username: str = "Anonymous"

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_token(token)
                user_id_str = payload.get("id")
                if user_id_str:
                    user_id = uuid.UUID(str(user_id_str))
                username = payload.get("sub", "Unknown")
            except Exception:
                pass  # Use anonymous if token is invalid

        # 3. Set ContextVars for CDC Hooks
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        set_audit_context(user_id, ip_address, username, user_agent)

        response = await call_next(request)

        # 4. Check Status Code Exclusion
        if response.status_code in settings.AUDIT_LOG_EXCLUDE_STATUS_CODES:
            return response

        # 5. Check Method Inclusion
        if request.method.upper() not in settings.AUDIT_LOG_INCLUDED_METHODS:
            return response

        # 6. Check Request State (set by skip_access_audit dependency)
        if hasattr(request.state, "skip_audit") and request.state.skip_audit:
            return response

        # 7. Log Access — engine resolved from app.state (FastAPI native pattern).
        try:
            with Session(request.app.state.engine) as session:
                log = AuditLog(
                    user_id=user_id,
                    username=username,
                    action="ACCESS",
                    entity_type="Endpoint",
                    entity_id=path,
                    changes={
                        "method": method,
                        "status_code": response.status_code,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.add(log)
                session.commit()
        except Exception as e:
            logger.error(
                "audit_log_error", error=str(e), path=path, method=method
            )

        return response
