"""
Constants and canonical domain enums for the Commerce module.
"""

from enum import Enum


class CommerceModuleSlug:
    GENERAL = "commerce"
    ROUNDS = "commerce_rounds"
    BATCHES = "commerce_batches"
    CATEGORIES = "commerce_categories"
    LIVE_BASKETS = "commerce_live_baskets"
    CHANNELS = "commerce_channels"
    PRODUCT_MASTERS = "commerce_product_masters"
    PRODUCTS = "commerce_products"
    SALES = "commerce_sales"


class SalePaymentMethod(str, Enum):
    QR = "QR"
    CASH = "CASH"
    TRANSFER = "TRANSFER"
    COURTESY = "COURTESY"


class SalePaymentStatus(str, Enum):
    COLLECTED = "COLLECTED"
    PENDING = "PENDING"
    COURTESY = "COURTESY"
    REFUNDED = "REFUNDED"


class SaleDeliveryModality(str, Enum):
    FREE_MEETING_POINT = "FREE_MEETING_POINT"
    HOME_DELIVERY = "HOME_DELIVERY"
    TERMINAL_BUS = "TERMINAL_BUS"
    NATIONAL_COURIER = "NATIONAL_COURIER"
    STORE_PICKUP = "STORE_PICKUP"
    PARCEL_SERVICE = "PARCEL_SERVICE"


class SaleDeliveryPaidBy(str, Enum):
    FREE = "FREE"
    CUSTOMER = "CUSTOMER"
    STORE = "STORE"


class SaleDeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    PENDING = "PENDING"


_PG_INT32_MAX = 2_147_483_647


def parse_search_int(
    search: str,
    prefixes: tuple[str, ...] = ("#", "NOV-", "VTA-"),
) -> int | None:
    """Extrae un entero positivo seguro (int32) desde un término de búsqueda.

    Evita crashes por dígitos Unicode como '³'/'²' donde `.isdigit()` es True
    pero `int()` falla, y evita desbordamientos int32 en PostgreSQL (barcodes).
    """
    cleaned = search.strip()
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if cleaned.upper().startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                changed = True

    if not cleaned or not (cleaned.isascii() and cleaned.isdigit()):
        return None

    val = int(cleaned)
    if val <= 0 or val > _PG_INT32_MAX:
        return None
    return val
