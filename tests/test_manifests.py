from sqlmodel import Session, select

from app.auth.service import AuthService
from app.core.manifests import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
    RolePermission,
    global_manifest_registry,
)
from app.core.manifests.registry import ManifestRegistry
from app.models.module import Module, ModuleGroup
from app.models.role import RoleModule
from app.models.user import User, UserRole


def test_manifest_sync_populates_database(session: Session):
    stats = global_manifest_registry.sync(session)

    assert stats["groups_upserted"] > 0
    assert stats["modules_upserted"] > 0
    assert stats["roles_upserted"] >= 1
    assert stats["role_modules_synced"] > 0

    # Verificar grupo Comercio
    commerce_group = session.exec(
        select(ModuleGroup).where(ModuleGroup.slug == "commerce")
    ).first()
    assert commerce_group is not None
    assert commerce_group.name == "Comercio"
    assert commerce_group.is_active is True

    # Verificar módulos de Comercio
    for slug in [
        "investment-rounds",
        "batches",
        "products",
        "product-masters",
        "sales",
        "commerce-catalogs",
    ]:
        mod = session.exec(select(Module).where(Module.slug == slug)).first()
        assert mod is not None, f"Module {slug} should exist in DB"
        assert mod.group_slug == "commerce"
        assert mod.is_active is True

    # Verificar que admin tiene permisos sobre los módulos de Comercio
    for slug in ["products", "batches", "sales"]:
        rm = session.exec(
            select(RoleModule).where(
                RoleModule.role_slug == "admin", RoleModule.module_slug == slug
            )
        ).first()
        assert rm is not None
        assert rm.can_create is True
        assert rm.can_update is True
        assert rm.can_delete is True
        assert rm.scope_all is True
        assert rm.is_active is True


def test_admin_menu_includes_commerce(session: Session):
    global_manifest_registry.sync(session)

    # Crear usuario superuser
    user = User(
        username="superadmin",
        email="admin@novabox.bo",
        password_hash="fakehash",
        is_superuser=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    auth_service = AuthService(session)
    menu = auth_service.get_role_menu(user, "admin")

    group_slugs = [g.slug for g in menu]
    assert "commerce" in group_slugs
    assert "configuration" in group_slugs
    assert "institution" not in group_slugs
    assert "fixed-assets" not in group_slugs

    commerce_menu = next(g for g in menu if g.slug == "commerce")
    assert commerce_menu.group_name == "Comercio"
    module_slugs = [m.slug for m in commerce_menu.modules]
    assert "products" in module_slugs
    assert "batches" in module_slugs
    assert "sales" in module_slugs


def test_manifest_soft_deactivation(session: Session):
    # Usar un registry aislado para probar desactivación suave
    test_reg = ManifestRegistry()

    m1 = DomainManifest(
        domain_name="test_domain",
        groups=[
            GroupDefinition(
                name="Test Group",
                slug="test-group",
                modules=[
                    ModuleDefinition(
                        name="Module 1",
                        slug="mod-1",
                        group_slug="test-group",
                        permissions={"manager": RolePermission()},
                    ),
                    ModuleDefinition(
                        name="Module 2",
                        slug="mod-2",
                        group_slug="test-group",
                    ),
                ],
            )
        ],
    )
    test_reg.register(m1)
    test_reg.sync(session)

    # Verificar que ambos módulos existen y están activos
    mod1 = session.exec(select(Module).where(Module.slug == "mod-1")).first()
    mod2 = session.exec(select(Module).where(Module.slug == "mod-2")).first()
    assert mod1 is not None and mod1.is_active is True
    assert mod2 is not None and mod2.is_active is True

    # Ahora simulamos que un desarrollador quita "mod-2" del manifest
    test_reg_updated = ManifestRegistry()
    m2 = DomainManifest(
        domain_name="test_domain",
        groups=[
            GroupDefinition(
                name="Test Group",
                slug="test-group",
                modules=[
                    ModuleDefinition(
                        name="Module 1",
                        slug="mod-1",
                        group_slug="test-group",
                    )
                ],
            )
        ],
    )
    test_reg_updated.register(m2)
    test_reg_updated.sync(session, soft_delete_missing=True)

    # Verificar mod-2: debe seguir existiendo en la BD pero con is_active=False
    mod2_after = session.exec(select(Module).where(Module.slug == "mod-2")).first()
    assert mod2_after is not None
    assert mod2_after.is_active is False

    # mod-1 sigue activo
    mod1_after = session.exec(select(Module).where(Module.slug == "mod-1")).first()
    assert mod1_after is not None
    assert mod1_after.is_active is True


def test_admin_user_role_auto_linked(session: Session):
    admin_user = User(
        username="admin",
        email="admin@uyuni.bo",
        password_hash="fakehash",
        is_superuser=True,
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)

    # Before sync, admin has no UserRole
    ur_before = session.exec(
        select(UserRole).where(UserRole.user_id == admin_user.id)
    ).first()
    assert ur_before is None

    # Sync manifests
    global_manifest_registry.sync(session)

    # After sync, UserRole is linked
    ur_after = session.exec(
        select(UserRole).where(UserRole.user_id == admin_user.id)
    ).first()
    assert ur_after is not None
    assert ur_after.role_slug == "admin"
    assert ur_after.is_active is True
