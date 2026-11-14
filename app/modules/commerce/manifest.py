"""
Manifiesto de dominio para el módulo Commerce.
Declara los grupos y submódulos de productos, lotes, ventas,
canastas live y catálogo maestro.
"""

from app.core.manifests.models import (
    DomainManifest,
    GroupDefinition,
    ModuleDefinition,
)
from app.core.manifests.registry import global_manifest_registry

commerce_manifest = DomainManifest(
    domain_name="commerce",
    groups=[
        GroupDefinition(
            name="Comercio",
            slug="commerce",
            description="Gestión Comercial, Lotes y Ventas",
            sort_order=5,
            icon="pi pi-shopping-bag",
            is_active=True,
            modules=[
                ModuleDefinition(
                    name="Rondas de Inversión",
                    slug="investment-rounds",
                    description=(
                        "Fondos de inversión, aportes de capital y punto de equilibrio"
                    ),
                    group_slug="commerce",
                    sort_order=1,
                    icon="pi pi-chart-line",
                    route="commerce/rounds",
                    is_active=True,
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
                ),
                ModuleDefinition(
                    name="Productos",
                    slug="products",
                    description="Catálogo de SKUs, estados y precios",
                    group_slug="commerce",
                    sort_order=3,
                    icon="pi pi-tags",
                    route="commerce/products",
                    is_active=True,
                ),
                ModuleDefinition(
                    name="Catálogo Maestro",
                    slug="product-masters",
                    description="Plantillas maestras de especificaciones de productos",
                    group_slug="commerce",
                    sort_order=4,
                    icon="pi pi-database",
                    route="commerce/product-masters",
                    is_active=True,
                ),
                ModuleDefinition(
                    name="Ventas",
                    slug="sales",
                    description="Registro atómico de ventas, canales y comisiones",
                    group_slug="commerce",
                    sort_order=5,
                    icon="pi pi-shopping-cart",
                    route="commerce/sales",
                    is_active=True,
                ),
                ModuleDefinition(
                    name="Catálogos",
                    slug="commerce-catalogs",
                    description=(
                        "Catálogos de soporte: categorías, canales de venta y "
                        "canastas live"
                    ),
                    group_slug="commerce",
                    sort_order=6,
                    icon="pi pi-sliders-h",
                    route="commerce/catalogs",
                    is_active=True,
                ),
            ],
        ),
    ],
)

global_manifest_registry.register(commerce_manifest)
