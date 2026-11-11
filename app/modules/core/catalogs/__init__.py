from app.core.catalogs.registry import global_registry
from app.modules.core.catalogs.providers import CoreRolesProvider

global_registry.register("core_roles", CoreRolesProvider())
global_registry.register("roles", CoreRolesProvider())
