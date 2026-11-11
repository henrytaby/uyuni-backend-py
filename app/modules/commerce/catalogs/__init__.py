from app.core.catalogs.registry import global_registry
from app.modules.commerce.catalogs.providers import (
    CommerceBatchesProvider,
    CommerceCategoriesProvider,
    CommerceDeliveryModalitiesProvider,
    CommerceDeliveryPaidByProvider,
    CommerceDeliveryStatusesProvider,
    CommerceInvestmentRoundsProvider,
    CommerceLiveBasketsProvider,
    CommercePaymentMethodsProvider,
    CommercePaymentStatusesProvider,
    CommercePhysicalConditionsProvider,
    CommerceProductMastersProvider,
    CommerceProductStatusesProvider,
    CommerceSalesChannelsProvider,
)

# Auto-registro de proveedores del dominio Commerce en el Registry global
global_registry.register("commerce_categories", CommerceCategoriesProvider())
global_registry.register("commerce_live_baskets", CommerceLiveBasketsProvider())
global_registry.register("commerce_batches", CommerceBatchesProvider())
global_registry.register(
    "commerce_physical_conditions", CommercePhysicalConditionsProvider()
)
global_registry.register("commerce_product_statuses", CommerceProductStatusesProvider())
global_registry.register(
    "commerce_investment_rounds", CommerceInvestmentRoundsProvider()
)
global_registry.register("commerce_sales_channels", CommerceSalesChannelsProvider())
global_registry.register("commerce_payment_statuses", CommercePaymentStatusesProvider())
global_registry.register(
    "commerce_delivery_modalities", CommerceDeliveryModalitiesProvider()
)
global_registry.register("commerce_delivery_paid_by", CommerceDeliveryPaidByProvider())
global_registry.register("commerce_payment_methods", CommercePaymentMethodsProvider())
global_registry.register(
    "commerce_delivery_statuses", CommerceDeliveryStatusesProvider()
)
global_registry.register("commerce_product_masters", CommerceProductMastersProvider())
