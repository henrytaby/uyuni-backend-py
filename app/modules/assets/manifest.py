"""
Manifiesto de dominio para el módulo Assets (Activos Fijos).
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
    RolePermission,
)
from app.core.manifests.registry import global_manifest_registry

assets_manifest = DomainManifest(
    domain_name="assets",
    groups=[
        GroupDefinition(
            name="Activos Fijos",
            slug="fixed-assets",
            description="Gestión y Control de Activos Fijos Institucionales",
            sort_order=4,
            icon="pi pi-box",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Activos",
                    slug="fixed-assets",
                    description="Inventario y Asignación de Activos Fijos",
                    group_slug="fixed-assets",
                    sort_order=1,
                    icon="pi pi-box",
                    route="fixed-assets",
                    is_active=True,
                    permissions={
                        "manager": RolePermission(
                            can_create=True,
                            can_update=True,
                            can_delete=True,
                            scope_all=True,
                        ),
                        "administration": RolePermission(
                            can_create=True,
                            can_update=True,
                            can_delete=True,
                            scope_all=False,
                        ),
                    },
                ),
            ],
        ),
    ],
)

global_manifest_registry.register(assets_manifest)
