from datetime import timedelta

from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlmodel import select

from app.auth import schemas, utils
from app.auth.schemas import ModuleGroupMenu, ModuleMenu, RoleInfo, UserModulePermission
from app.core.db import SessionDep
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

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
        user_agent = request.headers.get("user-agent") if request else "unknown"

        user = utils.authenticate_user(
            self.session, form_data.username, form_data.password
        )
        if not user:
            # Log the failed login attempt
            log = UserLogLogin(
                user_id=None,
                username=form_data.username,
                password=None, # Never log the password
                token=None,
                token_expiration=None,
                ip_address=ip_address,
                host_info=user_agent,
                is_successful=False,
            )

            self.session.add(log)
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token, refresh_token, access_token_expires = self._create_tokens(user)

        # Log the login attempt
        log = UserLogLogin(
            user_id=user.id,
            username=user.username,
            token=access_token,
            token_expiration=get_current_time() + access_token_expires,
            ip_address=ip_address,
            host_info=user_agent,
            is_successful=True,
        )

        self.session.add(log)
        self.session.commit()
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
        }

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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            ) from None

        user = utils.get_user(self.session, username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Check if the refresh token is already revoked
        query_revoked = select(UserRevokedToken).where(
            UserRevokedToken.token == refresh_token
        )
        revoked_token = self.session.exec(query_revoked).first()
        if revoked_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from None

        # Check if the access token is already revoked
        query = select(UserRevokedToken).where(UserRevokedToken.token == token)
        revoked_token = self.session.exec(query).first()
        if not revoked_token:
            revoked_token = UserRevokedToken(token=token, user_id=user_id)
            self.session.add(revoked_token)

        # Revoke Refresh Token if provided
        if refresh_token:
            query_rf = select(UserRevokedToken).where(
                UserRevokedToken.token == refresh_token
            )
            revoked_rf = self.session.exec(query_rf).first()
            if not revoked_rf:
                revoked_rf = UserRevokedToken(token=refresh_token, user_id=user_id)
                self.session.add(revoked_rf)

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

        return [RoleInfo(id=r.id, name=r.name, icon=r.icon) for r in roles]

    def get_role_menu(self, user: User, role_id: int) -> list[ModuleGroupMenu]:
        # 1. Validate Access
        target_role = self._validate_role_access(user, role_id)

        # 2. Group Modules
        groups_map, modules_by_group = self._group_modules(target_role)

        # 3. Build & Sort Response
        return self._build_menu_structure(groups_map, modules_by_group)

    def _validate_role_access(self, user: User, role_id: int) -> Role:
        if user.is_superuser:
            target_role = self.session.get(Role, role_id)
            if not target_role or not target_role.is_active:
                raise HTTPException(
                    status_code=404, detail="Role not found or inactive"
                )
            return target_role

        # Check if user has this role active
        for ur in user.user_roles:
            if (
                ur.role_id == role_id
                and ur.is_active
                and ur.role
                and ur.role.is_active
            ):
                return ur.role

        raise HTTPException(
            status_code=403, detail="User does not have access to this role"
        )

    def _group_modules(
        self, target_role: Role
    ) -> tuple[dict[int, ModuleGroup], dict[int, list[ModuleMenu]]]:
        groups_map: dict[int, ModuleGroup] = {}
        modules_by_group: dict[int, list[ModuleMenu]] = {}

        for rm in target_role.role_modules:
            if not rm.is_active:
                continue

            module = rm.module
            if not module or not module.is_active:
                continue

            group = module.group
            if not group or not group.id:
                continue

            if group.id not in groups_map:
                groups_map[group.id] = group
                modules_by_group[group.id] = []

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
            modules_by_group[group.id].append(mod_menu)

        return groups_map, modules_by_group

    def _build_menu_structure(
        self,
        groups_map: dict[int, ModuleGroup],
        modules_by_group: dict[int, list[ModuleMenu]],
    ) -> list[ModuleGroupMenu]:
        result = []
        
        # Sort groups
        sorted_groups = sorted(
            groups_map.values(), key=lambda g: g.sort_order if g.sort_order else 0
        )

        for group in sorted_groups:
            if not group.id:
                continue
            
            modules = modules_by_group[group.id]
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
