import os
import sys
from sqlmodel import Session, select

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine
from app.models.module import Module, ModuleGroup
from app.models.role import Role, RoleModule


def sync_module_groups(session: Session):
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
            "name": "Institución",
            "slug": "institution",
            "description": "Datos de la Institución",
            "sort_order": 2,
            "icon": "pi pi-building",
            "is_active": True,
        },
        {
            "name": "Núcleo",
            "slug": "core",
            "description": "Núcleo, Datos",
            "sort_order": 3,
            "icon": "pi pi-database",
            "is_active": True,
        },
        {
            "name": "Activos Fijos",
            "slug": "fixed-assets",
            "description": "Gestión de Activos Fijos",
            "sort_order": 4,
            "icon": "pi pi-box",
            "is_active": True,
        },
    ]
    for data in module_groups:
        existing = session.exec(select(ModuleGroup).where(ModuleGroup.slug == data["slug"])).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            session.add(ModuleGroup(**data))
    session.commit()
    print("✅ ModuleGroups synced")


def sync_roles(session: Session):
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
    for data in roles:
        existing = session.exec(select(Role).where(Role.slug == data["slug"])).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            session.add(Role(**data))
    session.commit()
    print("✅ Roles synced")


def sync_modules(session: Session):
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
        # Group: Institución
        {
            "name": "Funcionarios",
            "slug": "staff",
            "description": "Gestión de Personal / Funcionarios",
            "group_slug": "institution",
            "sort_order": 1,
            "icon": "pi pi-users",
            "route": "staff",
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
    for data in modules:
        existing = session.exec(select(Module).where(Module.slug == data["slug"])).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            session.add(Module(**data))
    session.commit()
    print("✅ Modules synced")


def sync_role_modules(session: Session):
    role_modules = [
        # Admin - Access to everything
        {"role_slug": "admin", "module_slug": "users", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        {"role_slug": "admin", "module_slug": "roles", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        {"role_slug": "admin", "module_slug": "config", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        {"role_slug": "admin", "module_slug": "staff", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        {"role_slug": "admin", "module_slug": "fixed-assets", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        # Manager - Staff and Fixed Assets
        {"role_slug": "manager", "module_slug": "staff", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        {"role_slug": "manager", "module_slug": "fixed-assets", "scope_all": True, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
        # Administration - Fixed Assets
        {"role_slug": "administration", "module_slug": "fixed-assets", "scope_all": False, "can_create": True, "can_update": True, "can_delete": True, "is_active": True},
    ]

    for data in role_modules:
        existing = session.exec(
            select(RoleModule).where(
                RoleModule.role_slug == data["role_slug"],
                RoleModule.module_slug == data["module_slug"]
            )
        ).first()
        
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            session.add(RoleModule(**data))
            
    session.commit()
    print("✅ RoleModules synced")


def run_seeders():
    with Session(engine) as session:
        # We no longer clear data. We sync it safely.
        sync_module_groups(session)
        sync_roles(session)
        sync_modules(session)
        sync_role_modules(session)


if __name__ == "__main__":
    run_seeders()
