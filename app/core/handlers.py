import re

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .exceptions import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
    UnauthorizedException,
)

logger = structlog.get_logger()
property_logger = structlog.get_logger("api.error")


async def not_found_exception_handler(request: Request, exc: NotFoundException):
    property_logger.info("resource_not_found", detail=exc.detail)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    property_logger.warning("bad_request_error", detail=exc.detail)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    property_logger.warning("unauthorized_access", detail=exc.detail)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    property_logger.warning("forbidden_access", detail=exc.detail)
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def internal_server_error_handler(
    request: Request, exc: InternalServerErrorException
):
    property_logger.error("internal_server_error", detail=exc.detail)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    err_msg = str(exc)
    detail = "Error de integridad de datos."

    # Try to parse psycopg2 / postgresql diagnostics
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) if orig else None

    if pgcode:
        # PostgreSQL specific error codes
        diag = getattr(orig, "diag", None)
        message_detail = getattr(diag, "message_detail", None) if diag else None

        if pgcode == "23505":  # UniqueViolation
            if message_detail:
                match = re.search(
                    r"Key \((.*?)\)=\((.*?)\) already exists", message_detail
                )
                if match:
                    detail = (
                        f"Ya existe un registro con el valor '{match.group(2)}' "
                        f"para el campo '{match.group(1)}'."
                    )
                else:
                    detail = f"Valor duplicado: {message_detail}"
            else:
                detail = "El registro ya existe (violación de unicidad)."
        elif pgcode == "23503":  # ForeignKeyViolation
            if message_detail:
                match = re.search(
                    r"Key \((.*?)\)=\((.*?)\) is not present in table \"(.*?)\"",
                    message_detail,
                )
                if match:
                    detail = (
                        f"El valor '{match.group(2)}' especificado para el "
                        f"campo '{match.group(1)}' no existe en la tabla de "
                        f"referencia '{match.group(3)}'."
                    )
                else:
                    detail = f"Violación de clave foránea: {message_detail}"
            else:
                detail = "La relación referenciada no existe."
        elif pgcode == "23502":  # NotNullViolation
            column_name = getattr(diag, "column_name", None) if diag else None
            if column_name:
                detail = f"El campo '{column_name}' es requerido y no puede ser nulo."
            else:
                detail = "Un campo requerido no fue proporcionado."
        else:
            if message_detail:
                detail = f"Error de integridad: {message_detail}"
            elif orig is not None and hasattr(orig, "message"):
                detail = f"Error de integridad: {orig.message}"
    else:
        # Fallback to parsing the exception string (covers SQLite, etc.)
        err_msg_lower = err_msg.lower()
        if "unique constraint failed" in err_msg_lower:
            match = re.search(r"unique constraint failed: (.*)", err_msg, re.IGNORECASE)
            if match:
                fields = [f.split(".")[-1] for f in match.group(1).split(",")]
                detail = (
                    "Ya existe un registro con el valor duplicado en: "
                    f"{', '.join(fields)}."
                )
            else:
                detail = "Ya existe un registro con estos datos duplicados."
        elif (
            "foreign key constraint failed" in err_msg_lower
            or "foreignkeyviolation" in err_msg_lower
        ):
            # Check if Postgres error message is inside the exception string
            match = re.search(
                r"Key \((.*?)\)=\((.*?)\) is not present in table \"(.*?)\"",
                err_msg,
            )
            if match:
                detail = (
                    f"El valor '{match.group(2)}' especificado para el "
                    f"campo '{match.group(1)}' no existe en la tabla de "
                    f"referencia '{match.group(3)}'."
                )
            else:
                detail = (
                    "La relación especificada (clave foránea) no existe o no es válida."
                )
        elif "not null constraint failed" in err_msg_lower:
            match = re.search(
                r"not null constraint failed: (.*)", err_msg, re.IGNORECASE
            )
            if match:
                field = match.group(1).split(".")[-1]
                detail = f"El campo '{field}' es requerido y no puede ser nulo."
            else:
                detail = "Uno de los campos requeridos no puede ser nulo."
        else:
            # Generic fallback
            match_unique = re.search(r"Key \((.*?)\)=\((.*?)\) already exists", err_msg)
            match_fk = re.search(
                r"Key \((.*?)\)=\((.*?)\) is not present in table \"(.*?)\"",
                err_msg,
            )
            if match_unique:
                detail = (
                    f"Ya existe un registro con el valor '{match_unique.group(2)}' "
                    f"para el campo '{match_unique.group(1)}'."
                )
            elif match_fk:
                detail = (
                    f"El valor '{match_fk.group(2)}' especificado para el "
                    f"campo '{match_fk.group(1)}' no existe en la tabla de "
                    f"referencia '{match_fk.group(3)}'."
                )
            else:
                detail = "Error de integridad de datos."

    property_logger.warning("database_integrity_error", detail=detail, error=err_msg)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail},
    )
