from datetime import timedelta
from typing import NoReturn

from fastapi import Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlmodel import select

from app.auth import schemas, utils
from app.auth.schemas import ModuleGroupMenu, ModuleMenu, RoleInfo, UserModulePermission
from app.core.config import settings
from app.core.db import SessionDep
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.models.module import ModuleGroup
from app.models.role import Role
from app.models.user import User, UserLogLogin, UserRevokedToken
from app.util.datetime import get_current_time


class AuthService:
    def __init__(self, session: SessionDep):
        self.session = session

    # CREATE USER
    # ----------------------
    def create_user(self, user: schemas.UserCreate):
        query = select(User).where(User.username == user.username)
        db_user = self.session.exec(query).first()
        if db_user:
            raise BadRequestException(detail="Username already registered")

        hashed_password = utils.get_password_hash(user.password)
        user_data_dict = user.model_dump(exclude_unset=True)
        del user_data_dict["password"]
        user_data_dict["password_hash"] = hashed_password
        new_user = User(**user_data_dict)
        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        return new_user

    def login_for_access_token(
        self,
        form_data: OAuth2PasswordRequestForm,
        request: Request,
    ):
        ip_address = request.client.host if request and request.client else "unknown"
        user_agent = (
            request.headers.get("user-agent", "unknown") if request else "unknown"
        )

        # 0. Find User (Independent of password check)
        query = select(User).where(User.username == form_data.username)
        user_obj = self.session.exec(query).first()

        if not user_obj:
            # Fake verifying password to mitigate timing attacks
            utils.verify_password(
                form_data.password,
                "$2b$12$2QldhwW8iLfBYmgRv30PT.LvIhDHP7E6cFqrHEyhjkDckn65FohGK",
            )

            # Log the attack/failed attempt
            log = UserLogLogin(
                user_id=None,
                username=form_data.username,
                ip_address=ip_address,
                host_info=user_agent,
                is_successful=False,
            )
            self.session.add(log)
            self.session.commit()

            self._raise_invalid_credentials()

        # 1. Check Lockout
        self._check_account_lockout(user_obj)

        # 2. Verify Password
        if not utils.verify_password(form_data.password, user_obj.password_hash):
            self._handle_failed_login(user_obj, ip_address, user_agent)
            self._raise_invalid_credentials()

        # 3. Generate Tokens (Do this first to log them)
        access_token, refresh_token, access_token_expires = self._create_tokens(
            user_obj
        )

        # 4. Success (Log with token info)
        self._handle_successful_login(
            user_obj,
            ip_address,
            user_agent,
            token=access_token,
            expiration=access_token_expires,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
        }

    # PRIVATE HELPERS (Clean Code Extraction)
    # ---------------------------------------
    def _raise_invalid_credentials(self) -> NoReturn:
        raise UnauthorizedException(
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _check_account_lockout(self, user: User):
        """Verifies if the user is currently locked out."""
        if user.locked_until and user.locked_until > get_current_time():
            wait_seconds = int((user.locked_until - get_current_time()).total_seconds())
            raise ForbiddenException(
                detail={
                    "message": "Account is locked due to too many failed attempts.",
                    "code": "ACCOUNT_LOCKED",
                    "unlock_at": user.locked_until.isoformat(),
                    "wait_seconds": wait_seconds,
                    "max_attempts": settings.SECURITY_LOGIN_MAX_ATTEMPTS,
                    "lockout_minutes": settings.SECURITY_LOCKOUT_MINUTES,
                },
                headers={"Retry-After": str(wait_seconds)},
            )

    def _handle_failed_login(self, user: User, ip: str, user_agent: str):
        """Increments failure counter, checks limit, logs failure."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= settings.SECURITY_LOGIN_MAX_ATTEMPTS:
            user.locked_until = get_current_time() + timedelta(
                minutes=settings.SECURITY_LOCKOUT_MINUTES
            )

        self.session.add(user)

        # Log failure
        log = UserLogLogin(
            user_id=user.id,
            username=user.username,
            ip_address=ip,
            host_info=user_agent,
            is_successful=False,
        )
        self.session.add(log)
        self.session.commit()

    def _handle_successful_login(
        self, user: User, ip: str, user_agent: str, token: str, expiration: timedelta
    ):
        """Resets counters, updates stats, logs success."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = get_current_time()
        self.session.add(user)

        log = UserLogLogin(
            user_id=user.id,
            username=user.username,
            ip_address=ip,
            host_info=user_agent,
            is_successful=True,
            token=token,
            token_expiration=get_current_time() + expiration,
        )
        self.session.add(log)
        self.session.commit()

    def _create_tokens(self, user: User):
        access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=utils.REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = utils.create_access_token(
            data={
                "sub": user.username,
                "id": user.id,
                "email": user.email,
            },
            expires_delta=access_token_expires,
        )

        refresh_token = utils.create_access_token(
            data={
                "sub": user.username,
                "id": user.id,
                "email": user.email,
            },
            expires_delta=refresh_token_expires,
        )
        return access_token, refresh_token, access_token_expires

    def refresh_access_token(self, refresh_token: str):
        try:
            payload = utils.decode_token(refresh_token)
            username: str = payload.get("sub")
            if username is None:
                raise UnauthorizedException(detail="Invalid refresh token")
        except JWTError:
            raise UnauthorizedException(detail="Invalid refresh token") from None

        user = utils.get_user(self.session, username)
        if user is None:
            raise UnauthorizedException(detail="Invalid refresh token")

        # Check if the refresh token is already revoked
        query_revoked = select(UserRevokedToken).where(
            UserRevokedToken.token == refresh_token
        )
        revoked_token = self.session.exec(query_revoked).first()
        if revoked_token:
            raise UnauthorizedException(detail="Token has been revoked")

        # Revoke the old refresh token (Rotate)
        # Using 0 as user_id temporarily, or accurate user_id if we want
        # stricter validation earlier used_id for the record.
        new_revoked_token = UserRevokedToken(token=refresh_token, user_id=user.id)
        self.session.add(new_revoked_token)
        self.session.commit()

        access_token, new_refresh_token, _ = self._create_tokens(user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": new_refresh_token,
        }

    def logout(self, token: str, refresh_token: str | None = None):
        try:
            payload = utils.decode_token(token)
            user_id: int = payload.get("id")
            if user_id is None:
                raise UnauthorizedException(detail="Invalid token")
        except JWTError:
            raise UnauthorizedException(detail="Invalid token") from None

        # Check if the access token is already revoked
        query = select(UserRevokedToken).where(UserRevokedToken.token == token)
        revoked_token = self.session.exec(query).first()
        if not revoked_token:
            revoked_token = UserRevokedToken(token=token, user_id=user_id)
            self.session.add(revoked_token)

        # Revoke Refresh Token if provided
        if refresh_token:
            try:
                # Validate the refresh token before revoking
                rf_payload = utils.decode_token(refresh_token)
                rf_user_id: int = rf_payload.get("id")

                # Ensure the refresh token belongs to the user
                if rf_user_id != user_id:
                    raise UnauthorizedException(
                        detail="Invalid refresh token ownership"
                    )

                query_rf = select(UserRevokedToken).where(
                    UserRevokedToken.token == refresh_token
                )
                revoked_rf = self.session.exec(query_rf).first()
                if not revoked_rf:
                    revoked_rf = UserRevokedToken(token=refresh_token, user_id=user_id)
                    self.session.add(revoked_rf)

            except JWTError:
                # If refresh token is garbage or invalid signature, we can choose to:
                # 1. Ignore it (Log out successfully anyway)
                # 2. Raise Error (Strict)
                # Given strict security, raising error is safer
                # to signal client client issues.
                raise UnauthorizedException(detail="Invalid refresh token") from None

        # Update the log with logout time
        log_query = select(UserLogLogin).where(UserLogLogin.token == token)
        log = self.session.exec(log_query).first()
        if log:
            log.logged_out_at = get_current_time()
            self.session.add(log)

        self.session.commit()

    def get_user_roles(self, user: User) -> list[RoleInfo]:
        if user.is_superuser:
            # Superuser sees all active roles
            query = select(Role).where(Role.is_active).order_by(Role.sort_order)  # type: ignore
            roles = self.session.exec(query).all()
        else:
            # Normal user sees their assigned active roles
            # We filter by Role.is_active AND UserRole.is_active
            roles = []
            for ur in user.user_roles:
                if ur.is_active and ur.role and ur.role.is_active:
                    roles.append(ur.role)
            # Sort manually since we iterated
            roles.sort(key=lambda r: r.sort_order if r.sort_order else 0)

        return [
            RoleInfo(
                id=r.id,
                name=r.name,
                slug=r.slug,
                description=r.description,
                icon=r.icon,
            )
            for r in roles
        ]

    def get_role_menu(self, user: User, role_slug: str) -> list[ModuleGroupMenu]:
        # 1. Validate Access
        target_role = self._validate_role_access(user, role_slug)

        # 2. Group Modules
        groups_map, modules_by_group = self._group_modules(target_role)

        # 3. Build & Sort Response
        return self._build_menu_structure(groups_map, modules_by_group)

    def _validate_role_access(self, user: User, role_slug: str) -> Role:
        if user.is_superuser:
            query = select(Role).where(Role.slug == role_slug)
            target_role = self.session.exec(query).first()
            if not target_role or not target_role.is_active:
                raise NotFoundException(detail="Role not found or inactive")
            return target_role

        # Check if user has this role active
        for ur in user.user_roles:
            if (
                ur.role_slug == role_slug
                and ur.is_active
                and ur.role
                and ur.role.is_active
            ):
                return ur.role

        raise ForbiddenException(detail="User does not have access to this role")

    def _group_modules(
        self, target_role: Role
    ) -> tuple[dict[str, ModuleGroup], dict[str, list[ModuleMenu]]]:
        groups_map: dict[str, ModuleGroup] = {}
        modules_by_group: dict[str, list[ModuleMenu]] = {}

        for rm in target_role.role_modules:
            if not rm.is_active:
                continue

            module = rm.module
            if not module or not module.is_active:
                continue

            group = module.group
            if not group or not group.slug:
                continue

            if group.slug not in groups_map:
                groups_map[group.slug] = group
                modules_by_group[group.slug] = []

            # Create Permission & Menu Objects
            perms = UserModulePermission(
                module_slug=module.slug,
                can_create=rm.can_create,
                can_update=rm.can_update,
                can_delete=rm.can_delete,
                can_read=True,  # Implied
            )

            mod_menu = ModuleMenu(
                name=module.name,
                slug=module.slug,
                route=module.route,
                icon=module.icon,
                sort_order=module.sort_order,
                permissions=perms,
            )
            modules_by_group[group.slug].append(mod_menu)

        return groups_map, modules_by_group

    def _build_menu_structure(
        self,
        groups_map: dict[str, ModuleGroup],
        modules_by_group: dict[str, list[ModuleMenu]],
    ) -> list[ModuleGroupMenu]:
        result = []

        # Sort groups
        sorted_groups = sorted(
            groups_map.values(), key=lambda g: g.sort_order if g.sort_order else 0
        )

        for group in sorted_groups:
            if not group.slug:
                continue

            modules = modules_by_group[group.slug]
            # Sort modules within group
            modules.sort(key=lambda m: m.sort_order if m.sort_order else 0)

            group_menu = ModuleGroupMenu(
                group_name=group.name,
                slug=group.slug,
                icon=group.icon,
                sort_order=group.sort_order,
                modules=modules,
            )
            result.append(group_menu)

        return result
