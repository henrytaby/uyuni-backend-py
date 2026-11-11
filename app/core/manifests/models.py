from dataclasses import dataclass, field


@dataclass
class RolePermission:
    can_create: bool = True
    can_update: bool = True
    can_delete: bool = True
    scope_all: bool = True
    is_active: bool = True


@dataclass
class ModuleDefinition:
    name: str
    slug: str
    group_slug: str
    route: str | None = None
    icon: str | None = None
    description: str | None = None
    sort_order: int = 1
    is_active: bool = True
    permissions: dict[str, RolePermission] = field(default_factory=dict)


@dataclass
class GroupDefinition:
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    sort_order: int = 1
    is_active: bool = True
    modules: list[ModuleDefinition] = field(default_factory=list)


@dataclass
class RoleDefinition:
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    sort_order: int = 1
    is_active: bool = True


@dataclass
class DomainManifest:
    domain_name: str
    groups: list[GroupDefinition] = field(default_factory=list)
    roles: list[RoleDefinition] = field(default_factory=list)
