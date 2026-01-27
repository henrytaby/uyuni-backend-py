import pytest
from sqlmodel import Session

from app.auth.permissions import PermissionAction, PermissionChecker
from app.models.module import Module, ModuleGroup
from app.models.role import Role, RoleModule
from app.models.user import User, UserRole


def create_test_data(session: Session):
    # Create Module
    group = ModuleGroup(name="Test Group", slug="test-group")
    session.add(group)
    session.commit()
    session.refresh(group)

    module = Module(name="Test Module", slug="test-module", group_id=group.id)
    session.add(module)
    session.commit()
    session.refresh(module)

    # Create Roles
    # Role A: Can CREATE
    role_a = Role(name="Role A", slug="role-a", is_active=True)
    # Role B: Can DELETE
    role_b = Role(name="Role B", slug="role-b", is_active=True)
    # Role C: Unassigned but active
    role_c = Role(name="Role C", slug="role-c", is_active=True)

    session.add(role_a)
    session.add(role_b)
    session.add(role_c)
    session.commit()

    # Permissions
    rm_a = RoleModule(
        role_slug=role_a.slug,
        module_slug=module.slug,
        is_active=True,
        can_create=True,
        can_delete=False,
    )
    rm_b = RoleModule(
        role_slug=role_b.slug,
        module_slug=module.slug,
        is_active=True,
        can_create=False,
        can_delete=True,
    )
    rm_c = RoleModule(
        role_slug=role_c.slug,
        module_slug=module.slug,
        is_active=True,
        can_create=True,
        can_delete=True,
    )

    session.add(rm_a)
    session.add(rm_b)
    session.add(rm_c)
    session.commit()

    # User
    user = User(username="testuser", email="test@example.com", password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    # Assign Roles A and B
    ur_a = UserRole(user_id=user.id, role_slug=role_a.slug, is_active=True)
    ur_b = UserRole(user_id=user.id, role_slug=role_b.slug, is_active=True)
    session.add(ur_a)
    session.add(ur_b)
    session.commit()

    return user, module


def test_no_header_aggregated_permissions(session: Session):
    """Without header, permissions should be aggregated (Create + Delete)."""
    user, module = create_test_data(session)

    checker_create = PermissionChecker(
        module_slug="test-module", required_permission=PermissionAction.CREATE
    )
    # Remove checker_delete as it is unused
    pass

    # Mocking dependency calls manually since we are testing logic,
    # but normally we rely on integration tests.
    # Here we assume dependency injection works and test the __call__ logic.

    perms = checker_create(user=user, active_role_slug=None)
    assert perms.can_create is True
    assert perms.can_delete is True  # Aggregated from Role B


def test_active_role_a(session: Session):
    """With X-Active-Role: role-a, should only have Create."""
    user, module = create_test_data(session)

    checker = PermissionChecker(
        module_slug="test-module", required_permission=PermissionAction.CREATE
    )

    perms = checker(user=user, active_role_slug="role-a")
    assert perms.can_create is True
    assert perms.can_delete is False  # Role B is ignored


def test_active_role_b(session: Session):
    """With X-Active-Role: role-b, should only have Delete."""
    user, module = create_test_data(session)

    checker = PermissionChecker(
        module_slug="test-module", required_permission=PermissionAction.DELETE
    )

    perms = checker(user=user, active_role_slug="role-b")
    assert perms.can_create is False  # Role A is ignored
    assert perms.can_delete is True


def test_active_role_unassigned(session: Session):
    """Requesting unassigned Role C should fail."""
    user, module = create_test_data(session)

    checker = PermissionChecker(
        module_slug="test-module", required_permission=PermissionAction.READ
    )

    from app.core.exceptions import ForbiddenException

    with pytest.raises(ForbiddenException):
        checker(user=user, active_role_slug="role-c")
