"""
Sistema centralizado de manifiestos modulares (Domain Manifests).
Permite el auto-registro desacoplado de grupos de módulos, roles y permisos por dominio.
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
    RoleDefinition,
    RolePermission,
)
from app.core.manifests.registry import global_manifest_registry


def load_domain_manifests() -> None:
    """
    Importa todos los manifiestos de dominio para asegurar
    su registro en el Registry global.
    """
    import app.modules.assets.manifest  # noqa: F401
    import app.modules.commerce.manifest  # noqa: F401
    import app.modules.core.manifest  # noqa: F401


# Auto-carga al importar el paquete
load_domain_manifests()

__all__ = [
    "DomainManifest",
    "GroupDefinition",
    "ModuleDefinition",
    "RoleDefinition",
    "RolePermission",
    "global_manifest_registry",
    "load_domain_manifests",
]
