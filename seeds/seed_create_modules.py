from sqlmodel import Session, delete

from app.core.db import engine
from app.models.module import Module, ModuleGroup
from app.models.role import Role, RoleModule


def clear_data(session: Session):
    """Clear existing data in proper dependency order."""
    session.exec(delete(RoleModule))  # type: ignore
    session.exec(delete(Module))  # type: ignore
    session.exec(delete(Role))  # type: ignore
    session.exec(delete(ModuleGroup))  # type: ignore
    session.commit()
    print("✅ Data cleared: RoleModule, Module, Role, ModuleGroup")


def create_module_groups(session: Session):
    module_groups = [
        {
            "name": "Configuración",
            "slug": "configuration",
            "description": "Gestión de Usuarios",
            "sort_order": 1,
            "icon": "pi pi-cog",
            "is_active": True,
        },
        {
            "name": "Activos Fijos",
            "slug": "fixed-assets",
            "description": "Gestión de Activos Fijos",
            "sort_order": 2,
            "icon": "pi pi-building",
            "is_active": True,
        },
    ]
    for group_data in module_groups:
        group = ModuleGroup(**group_data)
        session.add(group)
    session.commit()
    print("✅ ModuleGroups created")


def create_roles(session: Session):
    roles = [
        {
            "name": "Administrador Sistema",
            "slug": "admin",
            "description": "Administrador de Sistema",
            "sort_order": 1,
            "icon": "pi pi-user",
            "is_active": True,
        },
        {
            "name": "Persona de Institución",
            "slug": "administration",
            "description": "Usuarios de la Administración",
            "sort_order": 2,
            "icon": "pi pi-building",
            "is_active": True,
        },
        {
            "name": "Gestor Admin",
            "slug": "manager",
            "description": "Administrador de la información",
            "sort_order": 3,
            "icon": "pi pi-database",
            "is_active": True,
        },
    ]
    for role_data in roles:
        role = Role(**role_data)
        session.add(role)
    session.commit()
    print("✅ Roles created")


def create_modules(session: Session):
    # Using group_slug directly as per new schema
    modules = [
        # Group: Configuración
        {
            "name": "Usuario",
            "slug": "users",
            "description": "Gestión de Usuarios",
            "group_slug": "configuration",
            "sort_order": 1,
            "icon": "pi pi-user",
            "route": "users",
            "is_active": True,
        },
        {
            "name": "Roles",
            "slug": "roles",
            "description": "Gestión de Roles",
            "group_slug": "configuration",
            "sort_order": 2,
            "icon": "pi pi-box",
            "route": "roles",
            "is_active": True,
        },
        {
            "name": "Configuración",
            "slug": "config",
            "description": "Configuración de Sistema",
            "group_slug": "configuration",
            "sort_order": 3,
            "icon": "pi pi-box",
            "route": "config",
            "is_active": True,
        },
        # Group: Activos Fijos
        {
            "name": "Activos",
            "slug": "fixed-assets",
            "description": "Gestión de Activos",
            "group_slug": "fixed-assets",
            "sort_order": 1,
            "icon": "pi pi-box",
            "route": "fixed-assets",
            "is_active": True,
        },
    ]
    for module_data in modules:
        module = Module(**module_data)
        session.add(module)
    session.commit()
    print("✅ Modules created")


def create_role_modules(session: Session):
    # Mapping roles to modules (slug to slug)
    role_modules = [
        # Admin - Users
        {
            "role_slug": "admin",
            "module_slug": "users",
            "scope_all": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
        # Admin - Roles
        {
            "role_slug": "admin",
            "module_slug": "roles",
            "scope_all": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
        # Admin - Config
        {
            "role_slug": "admin",
            "module_slug": "config",
            "scope_all": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
        # Admin - Fixed Assets
        {
            "role_slug": "admin",
            "module_slug": "fixed-assets",
            "scope_all": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
        # Administration - Fixed Assets (Personal Scope)
        {
            "role_slug": "administration",
            "module_slug": "fixed-assets",
            "scope_all": False,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
        # Manager - Fixed Assets (Scope All)
        {
            "role_slug": "manager",
            "module_slug": "fixed-assets",
            "scope_all": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "is_active": True,
        },
    ]

    for rm_data in role_modules:
        rm = RoleModule(**rm_data)
        session.add(rm)
    session.commit()
    print("✅ RoleModules created")


def run_seeders():
    with Session(engine) as session:
        clear_data(session)
        create_module_groups(session)
        create_roles(session)
        create_modules(session)
        create_role_modules(session)


if __name__ == "__main__":
    run_seeders()
