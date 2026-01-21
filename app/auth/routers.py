from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.auth import schemas, utils
from app.auth.service import AuthService
from app.core.db import get_session
from app.models.user import User as UserModel

router = APIRouter()


def get_auth_service(session: Session = Depends(get_session)):
    return AuthService(session)


@router.post("/register", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate, service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user
    """
    return service.create_user(user)


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    request: Request,
    service: AuthService = Depends(get_auth_service),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    return service.login_for_access_token(form_data, request)


@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: schemas.User = Depends(utils.get_current_user)):
    return current_user


@router.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    refresh_token: str, service: AuthService = Depends(get_auth_service)
):
    return service.refresh_access_token(refresh_token)


@router.post("/logout", response_model=dict)
async def logout(
    service: AuthService = Depends(get_auth_service),
    token: str = Depends(utils.oauth2_scheme),
    current_user: UserModel = Depends(utils.get_current_user),
    logout_data: schemas.LogoutRequest | None = None,
):
    refresh_token = logout_data.refresh_token if logout_data else None
    service.logout(token, refresh_token)
    return {"msg": "Successfully logged out"}


@router.get("/me/roles", response_model=list[schemas.RoleInfo])
async def read_users_roles(
    current_user: UserModel = Depends(utils.get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Get all active roles assigned to the current user (or all if superuser).
    """
    return service.get_user_roles(current_user)


@router.get(
    "/me/menu/{role_id}",
    response_model=list[schemas.ModuleGroupMenu],
    summary="Get user menu for role",
    description=(
        "Retrieves the hierarchical menu structure (Module Groups -> Modules) "
        "for the current user in the context of a specific Role. "
        "Validates that the user holds the role."
    ),
)
async def read_user_menu(
    role_id: int,
    current_user: UserModel = Depends(utils.get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return service.get_role_menu(current_user, role_id)
