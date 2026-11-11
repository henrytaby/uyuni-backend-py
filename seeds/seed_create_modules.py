import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session

from app.core.db import engine
from app.core.manifests import global_manifest_registry


def run_seeders(session: Session | None = None) -> dict:
    """
    Sincroniza todos los módulos, grupos, roles y permisos
    declarados en los manifiestos de dominio (app/modules/*/manifest.py).
    """
    if session is not None:
        return global_manifest_registry.sync(session)

    with Session(engine) as s:
        return global_manifest_registry.sync(s)


# Funciones de compatibilidad hacia atrás
def sync_module_groups(session: Session):
    return global_manifest_registry.sync(session)


def sync_roles(session: Session):
    return global_manifest_registry.sync(session)


def sync_modules(session: Session):
    return global_manifest_registry.sync(session)


def sync_role_modules(session: Session):
    return global_manifest_registry.sync(session)


if __name__ == "__main__":
    print("🚀 Sincronizando módulos desde los manifiestos de dominio...")
    stats = run_seeders()
    print("✅ Sincronización completada exitosamente:")
    for k, v in stats.items():
        print(f"   - {k}: {v}")
