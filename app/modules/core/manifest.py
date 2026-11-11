"""
Manifiesto de dominio para el módulo Core (Configuración e Institución).
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
)
from app.core.manifests.registry import global_manifest_registry

core_manifest = DomainManifest(
    domain_name="core",
    groups=[
        GroupDefinition(
            name="Configuración",
            slug="configuration",
            description="Gestión de Cuentas y Accesos de Usuario",
            sort_order=1,
            icon="pi pi-cog",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Usuarios",
                    slug="users",
                    description="Gestión de Cuentas de Usuario",
                    group_slug="configuration",
                    sort_order=1,
                    icon="pi pi-user",
                    route="users",
                    is_active=True,
                ),
            ],
        ),
    ],
)

global_manifest_registry.register(core_manifest)
