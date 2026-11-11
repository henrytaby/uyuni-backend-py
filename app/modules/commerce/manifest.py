"""
Manifiesto de dominio para el módulo Commerce (Nova Box Bolivia).
Declara los grupos y submódulos de productos, lotes, ventas,
canastas live y catálogo maestro.
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
    RolePermission,
)
from app.core.manifests.registry import global_manifest_registry

manager_commerce_perm = RolePermission(
    can_create=True,
    can_update=True,
    can_delete=False,
    scope_all=True,
    is_active=True,
)

commerce_manifest = DomainManifest(
    domain_name="commerce",
    groups=[
        GroupDefinition(
            name="Comercio",
            slug="commerce",
            description="Gestión Comercial, Lotes y Ventas Nova Box Bolivia",
            sort_order=5,
            icon="pi pi-shopping-bag",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Productos",
                    slug="products",
                    description="Catálogo de SKUs NOV-XXX, estados y precios",
                    group_slug="commerce",
                    sort_order=1,
                    icon="pi pi-tags",
                    route="commerce/products",
                    is_active=True,
                    permissions={"manager": manager_commerce_perm},
                ),
                ModuleDefinition(
                    name="Lotes y Cajas",
                    slug="batches",
                    description="Cajas importadas, costeo y punto de equilibrio",
                    group_slug="commerce",
                    sort_order=2,
                    icon="pi pi-box",
                    route="commerce/batches",
                    is_active=True,
                    permissions={"manager": manager_commerce_perm},
                ),
                ModuleDefinition(
                    name="Ventas",
                    slug="sales",
                    description="Registro atómico de ventas, canales y comisiones",
                    group_slug="commerce",
                    sort_order=3,
                    icon="pi pi-shopping-cart",
                    route="commerce/sales",
                    is_active=True,
                    permissions={"manager": manager_commerce_perm},
                ),
                ModuleDefinition(
                    name="Canastas Live",
                    slug="live-baskets",
                    description="Canastas dinámicas para transmisiones en vivo",
                    group_slug="commerce",
                    sort_order=4,
                    icon="pi pi-video",
                    route="commerce/live-baskets",
                    is_active=True,
                    permissions={"manager": manager_commerce_perm},
                ),
                ModuleDefinition(
                    name="Catálogo Maestro",
                    slug="product-masters",
                    description="Plantillas maestras de especificaciones de productos",
                    group_slug="commerce",
                    sort_order=5,
                    icon="pi pi-database",
                    route="commerce/product-masters",
                    is_active=True,
                    permissions={"manager": manager_commerce_perm},
                ),
            ],
        ),
    ],
)

global_manifest_registry.register(commerce_manifest)
