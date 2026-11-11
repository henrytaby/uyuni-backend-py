from typing import Any

import structlog
from sqlmodel import Session, select

from app.core.manifests.models import (
    DomainManifest,
    RoleDefinition,
    RolePermission,
)
from app.models.module import Module, ModuleGroup
from app.models.role import Role, RoleModule

logger = structlog.get_logger("core.manifests")


class ManifestRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, DomainManifest] = {}

    def register(self, manifest: DomainManifest) -> None:
        """Registra un manifiesto de dominio en el registro global."""
        self._manifests[manifest.domain_name] = manifest
        logger.info(
            "domain_manifest_registered",
            domain=manifest.domain_name,
            groups_count=len(manifest.groups),
        )

    def get_manifests(self) -> list[DomainManifest]:
        return list(self._manifests.values())

    def sync(
        self, session: Session, soft_delete_missing: bool = True
    ) -> dict[str, Any]:
        """
        Sincroniza de forma idempotente todos los grupos, módulos, roles
        y permisos declarados en los manifiestos registrados.
        """
        stats = {
            "groups_upserted": 0,
            "groups_deactivated": 0,
            "modules_upserted": 0,
            "modules_deactivated": 0,
            "roles_upserted": 0,
            "role_modules_synced": 0,
        }

        # 1. Base Roles
        system_roles = [
            RoleDefinition(
                name="Administrador Sistema",
                slug="admin",
                description="Administrador de Sistema",
                sort_order=1,
                icon="pi pi-user",
            ),
            RoleDefinition(
                name="Persona de Institución",
                slug="administration",
                description="Usuarios de la Administración",
                sort_order=2,
                icon="pi pi-building",
            ),
            RoleDefinition(
                name="Gestor Admin",
                slug="manager",
                description="Administrador de la información",
                sort_order=3,
                icon="pi pi-database",
            ),
        ]

        # Agregar roles adicionales declarados en dominios
        for manifest in self._manifests.values():
            system_roles.extend(manifest.roles)

        for r_def in system_roles:
            role_obj = session.exec(select(Role).where(Role.slug == r_def.slug)).first()
            if role_obj:
                role_obj.name = r_def.name
                role_obj.description = r_def.description
                role_obj.sort_order = r_def.sort_order
                role_obj.icon = r_def.icon
                role_obj.is_active = r_def.is_active
            else:
                session.add(
                    Role(
                        name=r_def.name,
                        slug=r_def.slug,
                        description=r_def.description,
                        sort_order=r_def.sort_order,
                        icon=r_def.icon,
                        is_active=r_def.is_active,
                    )
                )
            stats["roles_upserted"] += 1
        session.flush()

        # 2. Module Groups
        active_group_slugs: set[str] = set()
        for manifest in self._manifests.values():
            for g_def in manifest.groups:
                active_group_slugs.add(g_def.slug)
                group_obj = session.exec(
                    select(ModuleGroup).where(ModuleGroup.slug == g_def.slug)
                ).first()
                if group_obj:
                    group_obj.name = g_def.name
                    group_obj.description = g_def.description
                    group_obj.sort_order = g_def.sort_order
                    group_obj.icon = g_def.icon
                    group_obj.is_active = g_def.is_active
                else:
                    session.add(
                        ModuleGroup(
                            name=g_def.name,
                            slug=g_def.slug,
                            description=g_def.description,
                            sort_order=g_def.sort_order,
                            icon=g_def.icon,
                            is_active=g_def.is_active,
                        )
                    )
                stats["groups_upserted"] += 1

        if soft_delete_missing:
            all_groups = session.exec(select(ModuleGroup)).all()
            for g in all_groups:
                if g.slug not in active_group_slugs and g.is_active:
                    g.is_active = False
                    stats["groups_deactivated"] += 1
                    logger.info("module_group_deactivated", slug=g.slug)
        session.flush()

        # 3. Modules & Role Permissions
        active_module_slugs: set[str] = set()
        for manifest in self._manifests.values():
            for g_def in manifest.groups:
                for m_def in g_def.modules:
                    active_module_slugs.add(m_def.slug)
                    mod_obj = session.exec(
                        select(Module).where(Module.slug == m_def.slug)
                    ).first()
                    if mod_obj:
                        mod_obj.name = m_def.name
                        mod_obj.description = m_def.description
                        mod_obj.icon = m_def.icon
                        mod_obj.route = m_def.route
                        mod_obj.sort_order = m_def.sort_order
                        mod_obj.group_slug = m_def.group_slug
                        mod_obj.is_active = m_def.is_active
                    else:
                        session.add(
                            Module(
                                name=m_def.name,
                                slug=m_def.slug,
                                description=m_def.description,
                                icon=m_def.icon,
                                route=m_def.route,
                                sort_order=m_def.sort_order,
                                group_slug=m_def.group_slug,
                                is_active=m_def.is_active,
                            )
                        )
                    stats["modules_upserted"] += 1
                    session.flush()

                    # Configurar permisos para este módulo
                    # Regla: Admin siempre tiene acceso total a módulos activos
                    admin_perm = m_def.permissions.get(
                        "admin",
                        RolePermission(
                            can_create=True,
                            can_update=True,
                            can_delete=True,
                            scope_all=True,
                            is_active=m_def.is_active,
                        ),
                    )

                    all_perms = dict(m_def.permissions)
                    all_perms["admin"] = admin_perm

                    for role_slug, perm in all_perms.items():
                        rm_obj = session.exec(
                            select(RoleModule).where(
                                RoleModule.role_slug == role_slug,
                                RoleModule.module_slug == m_def.slug,
                            )
                        ).first()

                        effective_is_active = perm.is_active and m_def.is_active
                        if rm_obj:
                            rm_obj.can_create = perm.can_create
                            rm_obj.can_update = perm.can_update
                            rm_obj.can_delete = perm.can_delete
                            rm_obj.scope_all = perm.scope_all
                            rm_obj.is_active = effective_is_active
                        else:
                            session.add(
                                RoleModule(
                                    role_slug=role_slug,
                                    module_slug=m_def.slug,
                                    can_create=perm.can_create,
                                    can_update=perm.can_update,
                                    can_delete=perm.can_delete,
                                    scope_all=perm.scope_all,
                                    is_active=effective_is_active,
                                )
                            )
                        stats["role_modules_synced"] += 1

        if soft_delete_missing:
            all_modules = session.exec(select(Module)).all()
            for m in all_modules:
                if m.slug not in active_module_slugs and m.is_active:
                    m.is_active = False
                    stats["modules_deactivated"] += 1
                    # También desactivar en RoleModule para que salga del menú
                    rms = session.exec(
                        select(RoleModule).where(RoleModule.module_slug == m.slug)
                    ).all()
                    for rm in rms:
                        rm.is_active = False
                    logger.info("module_deactivated", slug=m.slug)

        session.commit()
        logger.info("modules_sync_completed", **stats)
        return stats


global_manifest_registry = ManifestRegistry()
