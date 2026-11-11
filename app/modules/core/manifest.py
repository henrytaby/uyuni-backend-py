"""
Manifiesto de dominio para el módulo Core (Configuración, Institución y Núcleo).
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
    RolePermission,
)
from app.core.manifests.registry import global_manifest_registry

core_manifest = DomainManifest(
    domain_name="core",
    groups=[
        GroupDefinition(
            name="Configuración",
            slug="configuration",
            description="Gestión de Usuarios, Roles y Parámetros del Sistema",
            sort_order=1,
            icon="pi pi-cog",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Usuario",
                    slug="users",
                    description="Gestión de Cuentas y Accesos de Usuario",
                    group_slug="configuration",
                    sort_order=1,
                    icon="pi pi-user",
                    route="users",
                    is_active=True,
                ),
                ModuleDefinition(
                    name="Roles",
                    slug="roles",
                    description="Gestión de Roles y Matriz de Permisos",
                    group_slug="configuration",
                    sort_order=2,
                    icon="pi pi-box",
                    route="roles",
                    is_active=True,
                ),
                ModuleDefinition(
                    name="Configuración",
                    slug="config",
                    description="Configuración Global del Sistema",
                    group_slug="configuration",
                    sort_order=3,
                    icon="pi pi-cog",
                    route="config",
                    is_active=True,
                ),
            ],
        ),
        GroupDefinition(
            name="Institución",
            slug="institution",
            description="Estructura Organizacional y Personal",
            sort_order=2,
            icon="pi pi-building",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Funcionarios",
                    slug="staff",
                    description="Gestión de Personal y Funcionarios",
                    group_slug="institution",
                    sort_order=1,
                    icon="pi pi-users",
                    route="staff",
                    is_active=True,
                    permissions={
                        "manager": RolePermission(
                            can_create=True,
                            can_update=True,
                            can_delete=True,
                            scope_all=True,
                        ),
                    },
                ),
            ],
        ),
        GroupDefinition(
            name="Núcleo",
            slug="core",
            description="Catálogos y Datos Maestros del Núcleo",
            sort_order=3,
            icon="pi pi-database",
            is_active=True,
            modules=[],
        ),
    ],
)

global_manifest_registry.register(core_manifest)
