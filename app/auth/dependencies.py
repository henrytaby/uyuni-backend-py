from typing import Optional

from fastapi import Header


async def get_active_role_slug(
    x_active_role: Optional[str] = Header(default=None, alias="X-Active-Role"),
) -> Optional[str]:
    """
    Extracts the X-Active-Role header from the request.
    This header is sent by the frontend to indicate which role context
    the user is currently operating in.
    """
    return x_active_role
