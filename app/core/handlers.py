from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
    UnauthorizedException,
)


async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def internal_server_error_handler(
    request: Request, exc: InternalServerErrorException
):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.detail},
        headers=exc.headers,
    )
