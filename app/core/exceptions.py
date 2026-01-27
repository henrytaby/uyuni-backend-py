from typing import Any, Optional


class CustomException(Exception):
    def __init__(self, detail: Any, headers: Optional[dict[str, str]] = None):
        self.detail = detail
        self.headers = headers


class NotFoundException(CustomException):
    """Raised when a resource is not found."""

    pass


class BadRequestException(CustomException):
    """Raised when a request is invalid."""

    pass


class UnauthorizedException(CustomException):
    """Raised when authentication fails."""

    pass


class ForbiddenException(CustomException):
    """Raised when permission is denied or account is locked."""

    pass


class InternalServerErrorException(CustomException):
    """Raised when an unexpected error occurs."""

    pass
