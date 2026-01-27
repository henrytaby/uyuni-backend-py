from enum import Enum

from fastapi import Depends

from app.auth.dependencies import get_active_role_slug
from app.auth.schemas import UserModulePermission
from app.auth.utils import get_current_user
from app.core.exceptions import ForbiddenException
from app.models.user import User


class PermissionAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class PermissionChecker:
    def __init__(self, module_slug: str, required_permission: PermissionAction):
        self.module_slug = module_slug
        self.required_permission = required_permission

    def __call__(
        self,
        user: User = Depends(get_current_user),
        active_role_slug: str | None = Depends(get_active_role_slug),
    ) -> UserModulePermission:
        if user.is_superuser:
            return UserModulePermission(
                module_slug=self.module_slug,
                can_create=True,
                can_update=True,
                can_delete=True,
                can_read=True,
                scope_all=True,
            )

        # Initialize permissions
        can_create = False
        can_update = False
        can_delete = False
        has_module_access = False
        scope_all = False

        # Filter roles if X-Active-Role is present
        roles_to_check = []
        if active_role_slug:
            # Personification Mode: Only use the active role
            # First, verify the user actually HAS this role assigned and active
            found_role = False
            for ur in user.user_roles:
                if (
                    ur.role_slug == active_role_slug
                    and ur.is_active
                    and ur.role
                    and ur.role.is_active
                ):
                    roles_to_check.append(ur.role)
                    found_role = True
                    break

            # If the user requested a role they don't have, deny access
            if not found_role:
                raise ForbiddenException(
                    detail=(
                        f"You do not have access to the active role "
                        f"'{active_role_slug}'"
                    )
                )
        else:
            # Legacy Mode: Aggregate all active roles
            for ur in user.user_roles:
                if ur.is_active and ur.role and ur.role.is_active:
                    roles_to_check.append(ur.role)

        # Iterate over selected roles and aggregate permissions
        for role in roles_to_check:
            for role_module in role.role_modules:
                # Check if this role_module corresponds to the requested module slug
                # Optimized: We compare slugs directly without loading the Module object
                if role_module.module_slug == self.module_slug:
                    # Check active status of the assignment
                    # Note: We checked role.is_active above.

                    # Optimization: If we trust the slug, we could skip loading module
                    # if we assume active.
                    # But module.is_active is a business rule.
                    if not role_module.is_active or (
                        role_module.module and not role_module.module.is_active
                    ):
                        continue

                    has_module_access = True
                    if role_module.can_create:
                        can_create = True
                    if role_module.can_update:
                        can_update = True
                    if role_module.can_delete:
                        can_delete = True
                    if role_module.scope_all:
                        scope_all = True

        # Determine READ permission (Implicit)
        can_read = has_module_access

        # Construct permission object
        user_permissions = UserModulePermission(
            module_slug=self.module_slug,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
            can_read=can_read,
            scope_all=scope_all,
        )

        # Validate required permission
        is_allowed = False
        if self.required_permission == PermissionAction.READ:
            is_allowed = can_read
        elif self.required_permission == PermissionAction.CREATE:
            is_allowed = can_create
        elif self.required_permission == PermissionAction.UPDATE:
            is_allowed = can_update
        elif self.required_permission == PermissionAction.DELETE:
            is_allowed = can_delete

        if not is_allowed:
            raise ForbiddenException(
                detail=(
                    f"You do not have '{self.required_permission}' "
                    f"permission for module '{self.module_slug}'"
                )
            )

        return user_permissions
