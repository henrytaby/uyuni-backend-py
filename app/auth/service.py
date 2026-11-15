import uuid
from datetime import timedelta
from typing import NoReturn

import jwt
from fastapi import Request
from fastapi.security import OAuth2PasswordRequestForm
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
from app.core.network import get_client_ip
from app.core.storage.cloudinary_service import cloudinary_service
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
        ip_address = get_client_ip(request)
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
            username = payload.get("sub")
            if username is None:
                raise UnauthorizedException(detail="Invalid refresh token")
        except jwt.InvalidTokenError:
            raise UnauthorizedException(detail="Invalid refresh token") from None

        user = utils.get_user(self.session, username)
        if user is None or not user.is_active:
            raise UnauthorizedException(detail="Invalid refresh token")

        # Check if the refresh token is already revoked
        query_revoked = select(UserRevokedToken).where(
            UserRevokedToken.token == refresh_token
        )
        revoked_token = self.session.exec(query_revoked).first()
        if revoked_token:
            raise UnauthorizedException(detail="Token has been revoked")

        # Revoke the old refresh token (Rotate)
        new_revoked_token = UserRevokedToken(token=refresh_token, user_id=user.id)
        self.session.add(new_revoked_token)
        self.session.commit()

        access_token, new_refresh_token, _ = self._create_tokens(user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": new_refresh_token,
        }

    def logout(
        self, token: str | None = None, refresh_token: str | None = None
    ) -> None:
        if not token and not refresh_token:
            raise UnauthorizedException(detail="Token or refresh token required")

        access_user_id: str | None = None
        refresh_user_id: str | None = None

        # 1. Validate Access Token if provided (allowing expired tokens during logout)
        if token:
            try:
                payload = utils.decode_token(token, verify_exp=False)
                access_user_id = payload.get("id")
                if access_user_id is None:
                    raise UnauthorizedException(detail="Invalid token")
            except jwt.InvalidTokenError:
                raise UnauthorizedException(detail="Invalid token") from None

        # 2. Validate Refresh Token if provided (allowing expired tokens during logout)
        if refresh_token:
            try:
                rf_payload = utils.decode_token(refresh_token, verify_exp=False)
                refresh_user_id = rf_payload.get("id")
                if refresh_user_id is None:
                    raise UnauthorizedException(detail="Invalid refresh token")
            except jwt.InvalidTokenError:
                raise UnauthorizedException(detail="Invalid refresh token") from None

        # 3. Ensure token ownership matches if both tokens are provided
        if access_user_id and refresh_user_id:
            if str(access_user_id) != str(refresh_user_id):
                raise UnauthorizedException(detail="Invalid refresh token ownership")

        effective_user_id = access_user_id or refresh_user_id
        if not effective_user_id:
            raise UnauthorizedException(detail="Could not determine user identity")

        user_uuid = uuid.UUID(str(effective_user_id))

        # 4. Revoke Access Token if provided
        if token:
            query = select(UserRevokedToken).where(UserRevokedToken.token == token)
            revoked_token = self.session.exec(query).first()
            if not revoked_token:
                revoked_token = UserRevokedToken(token=token, user_id=user_uuid)
                self.session.add(revoked_token)

            # Update the log with logout time
            log_query = select(UserLogLogin).where(UserLogLogin.token == token)
            log = self.session.exec(log_query).first()
            if log and not log.logged_out_at:
                log.logged_out_at = get_current_time()
                self.session.add(log)
        else:
            # If no access token provided, update the latest active session
            # for this user
            log_query = (
                select(UserLogLogin)
                .where(
                    UserLogLogin.user_id == user_uuid,
                    UserLogLogin.logged_out_at.is_(None),  # type: ignore
                )
                .order_by(UserLogLogin.created_at.desc())  # type: ignore
            )
            log = self.session.exec(log_query).first()
            if log:
                log.logged_out_at = get_current_time()
                self.session.add(log)

        # 5. Revoke Refresh Token if provided
        if refresh_token:
            query_rf = select(UserRevokedToken).where(
                UserRevokedToken.token == refresh_token
            )
            revoked_rf = self.session.exec(query_rf).first()
            if not revoked_rf:
                revoked_rf = UserRevokedToken(token=refresh_token, user_id=user_uuid)
                self.session.add(revoked_rf)

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
                scope_all=rm.scope_all,
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

    def update_profile(
        self, current_user: User, data: schemas.UserProfileUpdate
    ) -> User:
        update_dict = data.model_dump(exclude_unset=True)

        # Si se actualiza o remueve avatar_url y existía uno previo en Cloudinary,
        # eliminamos el archivo anterior para evitar acumulación de imágenes huérfanas
        if "avatar_url" in update_dict:
            old_avatar = current_user.avatar_url
            new_avatar = update_dict["avatar_url"]
            if old_avatar and old_avatar != new_avatar:
                cloudinary_service.delete_image_by_url(old_avatar)

        for key, value in update_dict.items():
            setattr(current_user, key, value)
        current_user.updated_at = get_current_time()
        self.session.add(current_user)
        self.session.commit()
        self.session.refresh(current_user)
        return current_user

    def remove_avatar(self, current_user: User) -> User:
        if current_user.avatar_url:
            cloudinary_service.delete_image_by_url(current_user.avatar_url)
            current_user.avatar_url = None
            current_user.updated_at = get_current_time()
            self.session.add(current_user)
            self.session.commit()
            self.session.refresh(current_user)
        return current_user

    def change_password(
        self, current_user: User, data: schemas.UserChangePassword
    ) -> dict[str, str]:
        if not utils.verify_password(data.current_password, current_user.password_hash):
            raise BadRequestException(detail="La contraseña actual es incorrecta")

        if data.current_password == data.new_password:
            raise BadRequestException(
                detail="La nueva contraseña no puede ser idéntica a la actual"
            )

        current_user.password_hash = utils.get_password_hash(data.new_password)
        current_user.updated_at = get_current_time()
        self.session.add(current_user)
        self.session.commit()
        self.session.refresh(current_user)
        return {"message": "Contraseña actualizada exitosamente"}
