from app.core.catalogs.registry import global_registry
from app.modules.core.catalogs.providers import DepartamentosProvider, GerenciasProvider

# Auto-registro de proveedores del dominio Core en el Registry global
global_registry.register("gerencias", GerenciasProvider())
global_registry.register("departamentos", DepartamentosProvider())
