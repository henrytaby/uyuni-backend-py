import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.catalogs.registry import global_registry
from app.core.exceptions import BadRequestException
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.batches.service import BatchService
from app.modules.commerce.categories.models import Category
from app.modules.commerce.categories.service import CategoryService
from app.modules.commerce.channels.models import SalesChannel
from app.modules.commerce.channels.service import SalesChannelService
from app.modules.commerce.live_baskets.models import LiveBasket
from app.modules.commerce.live_baskets.service import LiveBasketService
from app.modules.commerce.product_masters.models import (
    ProductImage,
    ProductMaster,
)
from app.modules.commerce.product_masters.service import (
    ProductMasterService,
    detect_portal,
)
from app.modules.commerce.products.models import Product
from app.modules.commerce.products.service import ProductService
from app.modules.commerce.rounds.models import InvestmentRound
from app.modules.commerce.rounds.service import InvestmentRoundService
from app.modules.commerce.sales.schemas import SaleCreate, SaleItemCreate
from app.modules.commerce.sales.service import SaleService


def make_master(
    session: Session,
    item_number: int = 1,
    name: str = "Producto Test",
    official_price: float = 100.0,
    minimum_price: float = 80.0,
    published_price: float = 0.0,
) -> ProductMaster:
    service = ProductMasterService(session)
    existing = service.get_by_item_number(item_number)
    if existing:
        return existing
    return service.create(
        ProductMaster(
            item_number=item_number,
            name=name,
            official_price=official_price,
            minimum_price=minimum_price,
            published_price=published_price,
        )
    )


def test_batch_cost_recalculation(session: Session):
    round_service = InvestmentRoundService(session)
    round_obj = round_service.create(
        InvestmentRound(
            code="RONDA-TEST-01",
            name="Ronda Piloto Test",
            capital_invested=5000.0,
        )
    )

    batch_service = BatchService(session)
    batch = batch_service.create(
        Batch(
            code="ATAUD-TEST",
            name="Caja Ataúd Test",
            investment_round_id=round_obj.id,
            purchase_price=4000.0,
            freight_cost=200.0,
            initial_items_count=50,
            merma_items_count=2,
        )
    )

    # 4000 + 200 = 4200. Sellable: 50 - 2 = 48. Unit cost: 4200 / 48 = 87.5
    assert batch.total_cost == 4200.0
    assert batch.sellable_items_count == 48
    assert batch.unit_cost == 87.5


def test_product_stock_and_status(session: Session):
    batch_service = BatchService(session)
    batch = batch_service.create(
        Batch(
            code="BATCH-PROD-TEST",
            name="Lote Test",
            purchase_price=1000.0,
            initial_items_count=10,
        )
    )

    master = make_master(
        session, 1, "Proyector Smart Test", official_price=500.0, minimum_price=400.0
    )
    product_service = ProductService(session)
    product = product_service.create(
        Product(
            master_product_id=master.id,
            batch_id=batch.id,
            initial_quantity=1,
        )
    )

    assert product.available_quantity == 1
    assert product.status == "AVAILABLE"


def test_sale_atomic_transaction_success(session: Session):
    batch_service = BatchService(session)
    batch = batch_service.create(
        Batch(
            code="BATCH-SALE-01",
            name="Lote Para Ventas",
            purchase_price=1000.0,
            freight_cost=0.0,
            initial_items_count=10,
            merma_items_count=0,
        )
    )
    # Unit cost = 1000 / 10 = 100.0 Bs

    master = make_master(
        session, 2, "Cámara 4G Solar Test", official_price=350.0, minimum_price=280.0
    )
    product_service = ProductService(session)
    product = product_service.create(
        Product(
            master_product_id=master.id,
            batch_id=batch.id,
            initial_quantity=1,
        )
    )

    sale_service = SaleService(session)
    sale_data = SaleCreate(
        customer_name="Juan Perez",
        channel="TikTok Live",
        payment_method="QR",
        payment_status="Cobrado",
        delivery_modality="Punto de Encuentro Gratis",
        items=[
            SaleItemCreate(
                product_id=product.id,
                quantity=1,
                unit_price=300.0,
            )
        ],
    )

    sale = sale_service.create(sale_data)

    assert sale.id is not None
    assert sale.total_collected == 300.0
    assert sale.total_cost == 100.0
    assert sale.net_profit == 200.0  # 300 - 100

    # Verify product stock updated in DB
    updated_product = product_service.get_by_id(product.id)
    assert updated_product is not None
    assert updated_product.available_quantity == 0
    assert updated_product.sold_quantity == 1
    assert updated_product.status == "SOLD_OUT"


def test_sale_stock_validation(session: Session):
    master = make_master(
        session, 3, "Ítem Agotado", official_price=100.0, minimum_price=80.0
    )
    product_service = ProductService(session)
    product = product_service.create(
        Product(
            master_product_id=master.id,
            initial_quantity=1,
            sold_quantity=1,
            available_quantity=0,
            status="SOLD_OUT",
        )
    )

    sale_service = SaleService(session)
    sale_data = SaleCreate(
        customer_name="Cliente Despistado",
        items=[
            SaleItemCreate(
                product_id=product.id,
                quantity=1,
                unit_price=100.0,
            )
        ],
    )

    with pytest.raises(BadRequestException) as exc_info:
        sale_service.create(sale_data)

    assert "Stock insuficiente" in str(exc_info.value.detail)


def test_sale_minimum_price_violation(session: Session):
    master = make_master(
        session, 4, "Dron Pro 4K", official_price=800.0, minimum_price=650.0
    )
    product_service = ProductService(session)
    product = product_service.create(
        Product(
            master_product_id=master.id,
            initial_quantity=1,
        )
    )

    sale_service = SaleService(session)
    # Attempt to sell at 500 Bs (below 650 Bs minimum) without authorization
    sale_data = SaleCreate(
        customer_name="Regateador Extremo",
        allow_below_minimum=False,
        items=[
            SaleItemCreate(
                product_id=product.id,
                quantity=1,
                unit_price=500.0,
            )
        ],
    )

    with pytest.raises(BadRequestException) as exc_info:
        sale_service.create(sale_data)

    assert "menor al mínimo" in str(exc_info.value.detail)


def test_sale_minimum_price_override_authorized(session: Session):
    master = make_master(
        session,
        5,
        "Herramienta Multifunción",
        official_price=200.0,
        minimum_price=150.0,
    )
    product_service = ProductService(session)
    product = product_service.create(
        Product(
            master_product_id=master.id,
            initial_quantity=1,
        )
    )

    sale_service = SaleService(session)
    # Sell at 120 Bs (below 150 Bs) WITH allow_below_minimum=True
    sale_data = SaleCreate(
        customer_name="Amigo de la Casa",
        allow_below_minimum=True,
        observations="Autorizado remate por falla estética menor",
        items=[
            SaleItemCreate(
                product_id=product.id,
                quantity=1,
                unit_price=120.0,
            )
        ],
    )

    sale = sale_service.create(sale_data)
    assert sale.id is not None
    assert sale.total_collected == 120.0


def test_commerce_catalog_providers(session: Session):
    category_service = CategoryService(session)
    category_service.create(
        Category(
            code="CAT-01",
            name="Hogar & Iluminación",
            icon="💡",
        )
    )

    live_basket_service = LiveBasketService(session)
    live_basket_service.create(
        LiveBasket(
            code="C1",
            name="Taller & Auto",
            label="Canasta 1 - Taller & Auto",
        )
    )

    # Test dynamic registration
    categories_provider = global_registry.get_provider("commerce_categories")
    cat_items = categories_provider.get_items(session)
    assert len(cat_items) >= 1
    assert any("Hogar & Iluminación" in item.label for item in cat_items)

    baskets_provider = global_registry.get_provider("commerce_live_baskets")
    basket_items = baskets_provider.get_items(session)
    assert len(basket_items) >= 1
    assert any("Canasta 1 - Taller & Auto" in item.label for item in basket_items)

    channel_service = SalesChannelService(session)
    channel_service.create(
        SalesChannel(
            code="TEST-CH-01",
            name="Canal de Prueba",
            is_active=True,
        )
    )

    channels_provider = global_registry.get_provider("commerce_sales_channels")
    channel_items = channels_provider.get_items(session)
    assert len(channel_items) >= 1
    assert any("Canal de Prueba" in item.label for item in channel_items)

    pay_status_provider = global_registry.get_provider("commerce_payment_statuses")
    pay_items = pay_status_provider.get_items(session)
    assert any(item.value == "COLLECTED" for item in pay_items)

    del_mod_provider = global_registry.get_provider("commerce_delivery_modalities")
    del_items = del_mod_provider.get_items(session)
    assert any(item.value == "FREE_MEETING_POINT" for item in del_items)

    del_paid_provider = global_registry.get_provider("commerce_delivery_paid_by")
    paid_items = del_paid_provider.get_items(session)
    assert any(item.value == "CUSTOMER" for item in paid_items)


def test_api_commerce_endpoints(client: TestClient, superuser_token_headers: dict):
    # 1. Create Round via API
    res_round = client.post(
        "/api/commerce/rounds/",
        headers=superuser_token_headers,
        json={"code": "API-R-01", "name": "Ronda API", "capital_invested": 3000.0},
    )
    assert res_round.status_code == 200
    round_id = res_round.json()["id"]

    # 2. Create Batch via API
    res_batch = client.post(
        "/api/commerce/batches/",
        headers=superuser_token_headers,
        json={
            "code": "API-B-01",
            "name": "Caja API",
            "investment_round_id": round_id,
            "purchase_price": 2500.0,
            "freight_cost": 100.0,
            "initial_items_count": 20,
            "merma_items_count": 0,
        },
    )
    assert res_batch.status_code == 200
    batch_data = res_batch.json()
    assert batch_data["unit_cost"] == 130.0  # 2600 / 20
    batch_id = batch_data["id"]

    # 3. Create Product Master via API (item_number es autogenerado por el backend)
    res_master = client.post(
        "/api/commerce/product-masters/",
        headers=superuser_token_headers,
        json={
            "name": "Almohadilla Térmica API",
            "official_price": 250.0,
            "minimum_price": 200.0,
        },
    )
    assert res_master.status_code == 200
    master_data = res_master.json()
    master_id = master_data["id"]
    assigned_num = master_data["item_number"]
    assert assigned_num > 0

    res_master_num = client.get(
        f"/api/commerce/product-masters/by-number/{assigned_num}",
        headers=superuser_token_headers,
    )
    assert res_master_num.status_code == 200
    assert res_master_num.json()["id"] == master_id

    res_master_res = client.get(
        f"/api/commerce/product-masters/resolve/{assigned_num}",
        headers=superuser_token_headers,
    )
    assert res_master_res.status_code == 200
    assert res_master_res.json()["item_number"] == assigned_num

    # 3.1. Create Product Inventory Item via API
    res_product = client.post(
        "/api/commerce/products/",
        headers=superuser_token_headers,
        json={
            "master_product_id": master_id,
            "batch_id": batch_id,
            "initial_quantity": 1,
        },
    )
    assert res_product.status_code == 200
    product_id = res_product.json()["id"]
    assert res_product.json()["name"] == "Almohadilla Térmica API"
    assert res_product.json()["official_price"] == 250.0

    # 4. List Products via API
    res_list = client.get("/api/commerce/products/", headers=superuser_token_headers)
    assert res_list.status_code == 200
    assert any(p["id"] == product_id for p in res_list.json())

    # 5. Create Channel and Sale via API
    res_ch = client.post(
        "/api/commerce/channels/",
        headers=superuser_token_headers,
        json={"code": "API-CH-01", "name": "WhatsApp Directo", "is_active": True},
    )
    assert res_ch.status_code == 200
    ch_id = res_ch.json()["id"]

    res_sale = client.post(
        "/api/commerce/sales/",
        headers=superuser_token_headers,
        json={
            "customer_name": "Cliente API",
            "channel_id": ch_id,
            "channel": "WHATSAPP",
            "payment_method": "QR",
            "payment_status": "COLLECTED",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "unit_price": 220.0,
                }
            ],
        },
    )
    assert res_sale.status_code == 200
    sale_data = res_sale.json()
    assert sale_data["channel_id"] == ch_id
    assert sale_data["total_collected"] == 220.0
    assert sale_data["net_profit"] == 90.0  # 220 - 130 unit cost

    # 6. Verify Product is now "SOLD_OUT"
    res_get_prod = client.get(
        f"/api/commerce/products/{product_id}", headers=superuser_token_headers
    )
    assert res_get_prod.status_code == 200
    assert res_get_prod.json()["status"] == "SOLD_OUT"
    assert res_get_prod.json()["available_quantity"] == 0

    # 7. Test Batch Recalculate Endpoint
    res_recalc = client.post(
        f"/api/commerce/batches/{batch_id}/recalculate",
        headers=superuser_token_headers,
    )
    assert res_recalc.status_code == 200
    assert res_recalc.json()["id"] == batch_id

    # 8. Test Allocate Relative Costs Endpoint
    res_alloc = client.post(
        f"/api/commerce/batches/{batch_id}/allocate-relative-costs?basis=official_price",
        headers=superuser_token_headers,
    )
    assert res_alloc.status_code == 200
    assert res_alloc.json()["id"] == batch_id


def test_batch_recalculation_and_sales_revaluation(session: Session):
    batch_service = BatchService(session)
    product_service = ProductService(session)
    sale_service = SaleService(session)

    # 1. Crear lote con costo de 1000 Bs
    batch = batch_service.create(
        Batch(
            code="LOT-TEST-DYN",
            name="Caja Dinámica",
            purchase_price=900.0,
            freight_cost=100.0,
            initial_items_count=0,
            merma_items_count=0,
        )
    )
    assert batch.total_cost == 1000.0
    assert batch.unit_cost == 0.0

    # 2. Agregar dos productos (5 unidades cada uno = 10 unidades vendibles)
    m1 = make_master(
        session, 10, "Audífonos Bluetooth", official_price=200.0, minimum_price=150.0
    )
    m2 = make_master(
        session, 11, "Cargador Rápido", official_price=80.0, minimum_price=50.0
    )
    p1 = product_service.create(
        Product(
            master_product_id=m1.id,
            batch_id=batch.id,
            initial_quantity=5,
        )
    )
    p2 = product_service.create(
        Product(
            master_product_id=m2.id,
            batch_id=batch.id,
            initial_quantity=5,
        )
    )

    # El lote debe haberse recalculado automáticamente: 1000 / 10 = 100.0 Bs
    updated_batch = batch_service.get_by_id(batch.id)
    assert updated_batch is not None
    assert updated_batch.initial_items_count == 10
    assert updated_batch.sellable_items_count == 10
    assert updated_batch.unit_cost == 100.0

    # 3. Registrar una venta de 2 audífonos a 180 Bs c/u
    sale = sale_service.create(
        SaleCreate(
            customer_name="Comprador Temprano",
            channel="Marketplace",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[
                SaleItemCreate(
                    product_id=p1.id,
                    quantity=2,
                    unit_price=180.0,
                )
            ],
        )
    )
    assert sale.total_collected == 360.0
    assert sale.total_cost == 200.0  # 2 * 100.0
    assert sale.net_profit == 160.0  # 360 - 200

    # 4. Desempacar más productos en la misma caja: agregar Producto 3 con 10 unidades
    # Ahora la caja tiene 20 unidades vendibles en total (5 + 5 + 10)
    # Nuevo costo unitario esperado: 1000 / 20 = 50.0 Bs
    m3 = make_master(
        session, 12, "Smartwatch Fit", official_price=300.0, minimum_price=200.0
    )
    product_service.create(
        Product(
            master_product_id=m3.id,
            batch_id=batch.id,
            initial_quantity=10,
        )
    )

    # El lote se actualiza automáticamente a 50.0 Bs
    batch_after_p3 = batch_service.get_by_id(batch.id)
    assert batch_after_p3 is not None
    assert batch_after_p3.initial_items_count == 20
    assert batch_after_p3.sellable_items_count == 20
    assert batch_after_p3.unit_cost == 50.0

    # ¡Y la venta previa debe haberse revaluado automáticamente!
    revalued_sale = sale_service.get_by_id(sale.id)
    assert revalued_sale is not None
    assert revalued_sale.total_collected == 360.0
    assert revalued_sale.total_cost == 100.0  # 2 * 50.0
    assert revalued_sale.net_profit == 260.0  # 360 - 100
    assert revalued_sale.items[0].unit_cost == 50.0
    assert revalued_sale.items[0].net_margin == 260.0

    # 5. Descubrir merma: marcar los 5 cargadores (p2) como dañados (merma)
    # Vendibles pasan de 20 a 15 (20 iniciales - 5 merma)
    # Nuevo costo esperado: 1000 / 15 = 66.67 Bs
    product_service.update(p2.id, {"merma_quantity": 5})

    batch_after_merma = batch_service.get_by_id(batch.id)
    assert batch_after_merma is not None
    assert batch_after_merma.initial_items_count == 20
    assert batch_after_merma.merma_items_count == 5
    assert batch_after_merma.sellable_items_count == 15
    assert batch_after_merma.unit_cost == 66.67

    # La venta previa debe ajustarse al nuevo costo post-merma
    sale_after_merma = sale_service.get_by_id(sale.id)
    assert sale_after_merma is not None
    assert sale_after_merma.total_collected == 360.0
    assert sale_after_merma.total_cost == 133.34  # 2 * 66.67
    assert sale_after_merma.net_profit == 226.66  # 360 - 133.34


def test_product_custom_cost_price_sale_without_batch(session: Session):
    product_service = ProductService(session)
    sale_service = SaleService(session)

    # Producto comprado a pedido / reventa directa local sin pertenecer a ninguna caja
    m = make_master(
        session,
        13,
        "Taladro Inalámbrico 20V",
        official_price=500.0,
        minimum_price=450.0,
    )
    product = product_service.create(
        Product(
            master_product_id=m.id,
            batch_id=None,
            cost_price=350.0,
            initial_quantity=1,
        )
    )

    sale = sale_service.create(
        SaleCreate(
            customer_name="Cliente Directo",
            channel="WhatsApp",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    quantity=1,
                    unit_price=500.0,
                )
            ],
        )
    )

    assert sale.total_collected == 500.0
    assert sale.total_cost == 350.0
    assert sale.net_profit == 150.0
    assert sale.items[0].unit_cost == 350.0
    assert sale.items[0].net_margin == 150.0


def test_allocate_relative_costs_penny_exact_and_positive_margins(
    session: Session,
):
    batch_service = BatchService(session)
    product_service = ProductService(session)
    sale_service = SaleService(session)

    # 1. Caja de liquidación con costo de 1000 Bs
    batch = batch_service.create(
        Batch(
            code="LOT-ALLOC-01",
            name="Caja de Prueba Ponderación",
            purchase_price=900.0,
            freight_cost=100.0,
            initial_items_count=13,
            merma_items_count=0,
        )
    )

    # 2. Productos de valores muy dispares:
    # 10 cables pequeños de 50 Bs (Valor = 500 Bs)
    # 3 proyectores de 500 Bs (Valor = 1500 Bs)
    # Valor total esperado: 2000 Bs. Factor de costo: 1000 / 2000 = 50%
    m_small = make_master(
        session, 14, "Cable USB-C Rápido", official_price=50.0, minimum_price=35.0
    )
    m_large = make_master(
        session, 15, "Proyector HD Smart", official_price=500.0, minimum_price=400.0
    )
    p_small = product_service.create(
        Product(
            master_product_id=m_small.id,
            batch_id=batch.id,
            initial_quantity=10,
        )
    )
    p_large = product_service.create(
        Product(
            master_product_id=m_large.id,
            batch_id=batch.id,
            initial_quantity=3,
        )
    )

    # 3. Venta previa del producto pequeño al precio de regateo (40 Bs)
    sale = sale_service.create(
        SaleCreate(
            customer_name="Cliente Gadgets",
            channel="Marketplace",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[
                SaleItemCreate(
                    product_id=p_small.id,
                    quantity=1,
                    unit_price=40.0,
                )
            ],
        )
    )

    # 4. Ejecutar la distribución ponderada de costos (Retail Inventory Method)
    batch_service.allocate_relative_costs(batch.id, basis="official_price")

    # 5. Verificar costos asignados
    updated_small = product_service.get_by_id(p_small.id)
    updated_large = product_service.get_by_id(p_large.id)
    assert updated_small is not None and updated_large is not None

    # Cable de 50 Bs -> 50% de costo = 25.0 Bs
    assert updated_small.cost_price == 25.0
    # Proyector de 500 Bs -> 50% de costo = 250.0 Bs
    assert updated_large.cost_price == 250.0

    # 6. VERIFICACIÓN CRÍTICA: La suma exacta de los costos es IGUAL al costo de la caja
    total_allocated = round(
        (updated_small.cost_price * 10) + (updated_large.cost_price * 3), 2
    )
    assert total_allocated == batch.total_cost  # 250 + 750 = 1000.00 Bs EXACTOS

    # 7. VERIFICACIÓN DE RENTABILIDAD POSITIVA:
    # La venta previa del cable a 40 Bs ahora tiene costo de 25 Bs -> GANANCIA de +15 Bs
    # ¡Se eliminó el falso margen negativo!
    revalued_sale = sale_service.get_by_id(sale.id)
    assert revalued_sale is not None
    assert revalued_sale.total_collected == 40.0
    assert revalued_sale.total_cost == 25.0
    assert revalued_sale.net_profit == 15.0  # 40 - 25 = +15 Bs (Positivo!)


def test_product_master_crud_and_resolution(session: Session):
    service = ProductMasterService(session)

    # 1. Crear Ficha Maestra con item_number limpio y marketing
    master = service.create(
        ProductMaster(
            item_number=53,
            name="Almohadilla Eléctrica Térmica 30x60 cm",
            official_price=180.0,
            minimum_price=130.0,
            is_published_marketplace=True,
            is_whatsapp_published=True,
            is_fb_verified=True,
        ),
        initial_marketplace_url="https://facebook.com/marketplace/item/123",
    )
    assert master.id is not None
    assert master.item_number == 53
    assert master.code is None
    assert master.is_published_marketplace is True
    assert master.is_whatsapp_published is True
    assert master.is_fb_verified is True
    assert master.marketplace_url == "https://facebook.com/marketplace/item/123"

    # 2. Búsqueda y resolución flexible
    # Por número entero
    by_num = service.get_by_item_number(53)
    assert by_num is not None and by_num.id == master.id

    # Por string "53"
    by_str = service.resolve_by_identifier("53")
    assert by_str is not None and by_str.id == master.id

    # Por formato legacy "NOV-053"
    by_nov = service.resolve_by_identifier("NOV-053")
    assert by_nov is not None and by_nov.id == master.id

    # Por formato almohadilla "#53"
    by_hash = service.resolve_by_identifier("#53")
    assert by_hash is not None and by_hash.id == master.id

    # 3. Validación de unicidad
    with pytest.raises(BadRequestException):
        service.create(
            ProductMaster(
                item_number=53,
                name="Duplicado",
            )
        )


def test_product_master_inventory_unification_and_stock_aggregation(session: Session):
    master_service = ProductMasterService(session)
    product_service = ProductService(session)
    batch_service = BatchService(session)
    sale_service = SaleService(session)

    # 1. Ficha Maestra #53
    master = master_service.create(
        ProductMaster(
            item_number=53,
            name="Almohadilla Térmica Eléctrica 30x60 cm",
            official_price=180.0,
            minimum_price=130.0,
        )
    )

    # 2. Dos cajas / lotes diferentes
    batch1 = batch_service.create(
        Batch(
            code="BOX-1",
            name="Ataúd 1",
            purchase_price=1000.0,
            initial_items_count=10,
        )
    )
    batch2 = batch_service.create(
        Batch(
            code="BOX-2",
            name="Ataúd 2",
            purchase_price=2000.0,
            initial_items_count=10,
        )
    )

    # 3. Registro de productos físicos en cada lote unificados bajo Master #53
    p1 = product_service.create(
        Product(
            sheet_row_id=53,
            batch_id=batch1.id,
            master_product_id=master.id,
            variant_name="Calor Seco y Húmedo",
            cost_price=100.0,
            initial_quantity=1,
            available_quantity=1,
        )
    )

    p2 = product_service.create(
        Product(
            sheet_row_id=165,
            batch_id=batch2.id,
            master_product_id=master.id,
            variant_name="Modelo TK-HP2412",
            cost_price=80.0,
            initial_quantity=1,
            available_quantity=1,
        )
    )

    # 4. Verificar agregación de existencias a nivel catálogo maestro (1 + 1 = 2)
    stock = master_service.get_stock_summary(master.id)
    assert stock["available"] == 2
    assert stock["sold"] == 0
    assert stock["merma"] == 0

    # 5. Filtrar inventario por master_product_id
    items = product_service.get_all(master_product_id=master.id)
    assert len(items) == 2
    item_rows = {it.sheet_row_id for it in items}
    assert 53 in item_rows
    assert 165 in item_rows

    # 6. Realizar venta del producto de la caja 2 (p2 / NOV-165)
    sale = sale_service.create(
        SaleCreate(
            customer_name="Comprador Fisioterapia",
            channel="Marketplace",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[
                SaleItemCreate(
                    product_id=p2.id,
                    quantity=1,
                    unit_price=150.0,
                )
            ],
        )
    )
    assert sale.id is not None

    # 7. Verificar existencias consolidadas tras la venta
    # Master #53 ahora tiene 1 disponible y 1 vendido
    updated_stock = master_service.get_stock_summary(master.id)
    assert updated_stock["available"] == 1
    assert updated_stock["sold"] == 1
    assert updated_stock["merma"] == 0

    # Y cada lote mantiene su contabilidad física y costo exacto
    refreshed_p1 = product_service.get_by_id(p1.id)
    refreshed_p2 = product_service.get_by_id(p2.id)
    assert refreshed_p1 is not None and refreshed_p1.available_quantity == 1
    assert refreshed_p2 is not None and refreshed_p2.available_quantity == 0
    assert refreshed_p2.status == "SOLD_OUT"


def test_commerce_catalogs_and_search(
    client: TestClient, superuser_token_headers: dict, session: Session
):
    # 1. Crear producto maestro
    master_service = ProductMasterService(session)
    master = master_service.create(
        ProductMaster(
            item_number=999,
            code="NOV-999",
            name="Teclado Mecánico RGB Test",
            official_price=350.0,
            minimum_price=300.0,
            is_active=True,
        )
    )

    product_service = ProductService(session)
    prod = product_service.create(
        Product(
            master_product_id=master.id,
            variant_name="Switch Azul",
            initial_quantity=5,
            available_quantity=5,
        )
    )

    # 2. Verificar que el provider de catálogos liste el nuevo master
    provider = global_registry.get_provider("commerce_product_masters")
    assert provider is not None
    items = provider.get_items(session)
    labels = [it.label for it in items]
    assert any("#999 - Teclado Mecánico RGB Test" in lbl for lbl in labels)

    # 3. Probar endpoint individual GET /api/catalogs/commerce_product_masters
    res = client.get(
        "/api/catalogs/commerce_product_masters", headers=superuser_token_headers
    )
    assert res.status_code == 200
    catalog_data = res.json()
    assert any(it["label"] == "#999 - Teclado Mecánico RGB Test" for it in catalog_data)

    # 4. Probar endpoint masivo POST /api/catalogs/bulk
    bulk_payload = {
        "commerce_product_masters": {},
        "commerce_categories": {},
        "commerce_batches": {},
    }
    res_bulk = client.post(
        "/api/catalogs/bulk", json=bulk_payload, headers=superuser_token_headers
    )
    assert res_bulk.status_code == 200
    bulk_data = res_bulk.json()
    assert "commerce_product_masters" in bulk_data
    assert "commerce_categories" in bulk_data
    assert "commerce_batches" in bulk_data

    # 5. Probar búsqueda en /api/commerce/products/ por nombre del master
    res_search_name = client.get(
        "/api/commerce/products/?search=Teclado", headers=superuser_token_headers
    )
    assert res_search_name.status_code == 200
    matched_prods = res_search_name.json()
    assert len(matched_prods) >= 1
    assert any(p["id"] == str(prod.id) for p in matched_prods)

    # 6. Probar búsqueda en /api/commerce/product-masters/ por item_number ("#999")
    res_search_num = client.get(
        "/api/commerce/product-masters/?search=%23999", headers=superuser_token_headers
    )
    assert res_search_num.status_code == 200
    matched_masters = res_search_num.json()
    assert len(matched_masters) == 1
    assert matched_masters[0]["item_number"] == 999


def test_product_master_images_service(session: Session):
    from unittest.mock import patch

    from app.modules.commerce.product_masters.schemas import (
        ProductImageReorderItem,
        ProductImageUpdate,
    )

    master = make_master(session, 1050, "Cámara Solar Test")
    service = ProductMasterService(session)

    mock_upload_responses = [
        {
            "url": "https://res.cloudinary.com/test/image/upload/v1/uyuni/products/1050/catalog/pic1.webp",
            "public_id": "uyuni/products/1050/catalog/pic1",
            "format": "webp",
            "bytes": 54321,
            "width": 1080,
            "height": 1080,
        },
        {
            "url": "https://res.cloudinary.com/test/image/upload/v1/uyuni/products/1050/catalog/pic2.webp",
            "public_id": "uyuni/products/1050/catalog/pic2",
            "format": "webp",
            "bytes": 65432,
            "width": 1080,
            "height": 1080,
        },
        {
            "url": "https://res.cloudinary.com/test/image/upload/v1/uyuni/products/1050/real/pic3.webp",
            "public_id": "uyuni/products/1050/real/pic3",
            "format": "webp",
            "bytes": 76543,
            "width": 800,
            "height": 600,
        },
    ]

    with (
        patch(
            "app.modules.commerce.product_masters.service.cloudinary_service.upload_image"
        ) as mock_upload,
        patch(
            "app.modules.commerce.product_masters.service.cloudinary_service.delete_image"
        ) as mock_delete,
    ):
        mock_upload.side_effect = mock_upload_responses
        mock_delete.return_value = True

        files_data = [
            {
                "content": b"fake-jpeg-bytes-1",
                "filename": "foto_frontal.jpg",
                "content_type": "image/jpeg",
            },
            {
                "content": b"fake-png-bytes-2",
                "filename": "foto_trasera.png",
                "content_type": "image/png",
            },
        ]

        # 1. Subida batch de 2 imágenes CATALOG
        created = service.add_images(
            master_id=master.id,
            files_data=files_data,
            image_type="CATALOG",
            is_cover=False,
        )
        assert len(created) == 2
        # La primera imagen se convierte automáticamente en portada
        assert created[0].is_cover is True
        assert created[0].sort_order == 1
        assert created[0].original_filename == "foto_frontal.jpg"
        assert created[1].is_cover is False
        assert created[1].sort_order == 2

        # Portada sincronizada en ProductMaster
        session.refresh(master)
        assert master.cover_image_url == mock_upload_responses[0]["url"]

        # 2. Subida de una 3ra imagen tipo REAL
        files_real = [
            {
                "content": b"fake-real-bytes-3",
                "filename": "unboxing_real.jpg",
                "content_type": "image/jpeg",
            }
        ]
        created_real = service.add_images(
            master_id=master.id,
            files_data=files_real,
            image_type="REAL",
            is_cover=False,
        )
        assert len(created_real) == 1
        assert created_real[0].image_type == "REAL"
        assert created_real[0].sort_order == 3
        assert created_real[0].is_cover is False

        # 3. Listar imágenes y filtrar por tipo
        all_imgs = service.get_images(master.id)
        assert len(all_imgs) == 3

        cat_imgs = service.get_images(master.id, image_type="CATALOG")
        assert len(cat_imgs) == 2

        real_imgs = service.get_images(master.id, image_type="REAL")
        assert len(real_imgs) == 1

        # 4. Cambiar portada a la segunda imagen
        img2_id = created[1].id
        updated_cover = service.set_cover_image(master.id, img2_id)
        assert updated_cover.is_cover is True
        session.refresh(master)
        assert master.cover_image_url == mock_upload_responses[1]["url"]

        # 5. Reordenar imágenes
        reorder_items = [
            ProductImageReorderItem(id=created_real[0].id, sort_order=1),
            ProductImageReorderItem(id=created[0].id, sort_order=2),
            ProductImageReorderItem(id=created[1].id, sort_order=3),
        ]
        reordered = service.reorder_images(master.id, reorder_items)
        assert reordered[0].id == created_real[0].id
        assert reordered[0].sort_order == 1

        # 6. Actualizar metadatos de una imagen
        service.update_image(
            master.id,
            created[0].id,
            ProductImageUpdate(title="Foto Frontal con Caja"),
        )
        updated_img0 = service.session.get(ProductImage, created[0].id)
        assert updated_img0 is not None
        assert updated_img0.title == "Foto Frontal con Caja"

        # 7. Eliminar imagen de portada: debe reasignar la siguiente disponible
        service.delete_image(master.id, img2_id)
        mock_delete.assert_called_with(mock_upload_responses[1]["public_id"])
        session.refresh(master)
        assert master.cover_image_url is not None

        # 8. Eliminar las restantes
        service.delete_image(master.id, created[0].id)
        service.delete_image(master.id, created_real[0].id)
        session.refresh(master)
        assert master.cover_image_url is None
        assert len(service.get_images(master.id)) == 0


def test_product_master_images_api(
    client: TestClient, session: Session, superuser_token_headers: dict[str, str]
):
    from unittest.mock import patch

    master = make_master(session, 1051, "Audífonos Bluetooth Test")

    mock_resp = {
        "url": "https://res.cloudinary.com/test/image/upload/v1/uyuni/products/1051/catalog/aud.webp",
        "public_id": "uyuni/products/1051/catalog/aud",
        "format": "webp",
        "bytes": 20480,
        "width": 600,
        "height": 600,
    }

    with (
        patch(
            "app.modules.commerce.product_masters.service.cloudinary_service.upload_image"
        ) as mock_up,
        patch(
            "app.modules.commerce.product_masters.service.cloudinary_service.delete_image"
        ) as mock_del,
    ):
        mock_up.return_value = mock_resp
        mock_del.return_value = True

        # 1. POST /api/commerce/product-masters/{id}/images
        files = [
            (
                "files",
                ("audifonos.jpg", b"fake-jpg-binary-stream", "image/jpeg"),
            )
        ]
        res = client.post(
            f"/api/commerce/product-masters/{master.id}/images",
            files=files,
            data={"image_type": "CATALOG", "is_cover": "true"},
            headers=superuser_token_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        img_id = data[0]["id"]
        assert data[0]["is_cover"] is True
        assert data[0]["url"] == mock_resp["url"]
        assert data[0]["image_type"] == "CATALOG"

        # 2. GET /api/commerce/product-masters/{id} debe incluir images e images_count
        res_master = client.get(
            f"/api/commerce/product-masters/{master.id}",
            headers=superuser_token_headers,
        )
        assert res_master.status_code == 200
        master_data = res_master.json()
        assert master_data["images_count"] == 1
        assert len(master_data["images"]) == 1
        assert master_data["cover_image_url"] == mock_resp["url"]

        # 3. GET /api/commerce/product-masters/{id}/images
        res_imgs = client.get(
            f"/api/commerce/product-masters/{master.id}/images",
            headers=superuser_token_headers,
        )
        assert res_imgs.status_code == 200
        assert len(res_imgs.json()) == 1

        # 4. PATCH /api/commerce/product-masters/{id}/images/{image_id}
        res_patch = client.patch(
            f"/api/commerce/product-masters/{master.id}/images/{img_id}",
            json={"title": "Audífonos In-Ear"},
            headers=superuser_token_headers,
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["title"] == "Audífonos In-Ear"

        # 4.b Verificar que PUT proteja cover_image_url y descarte manipulaciones
        res_put = client.put(
            f"/api/commerce/product-masters/{master.id}",
            json={
                "name": "Audífonos Bluetooth Pro",
                "cover_image_url": "https://fake-link.com/invalido.png",
            },
            headers=superuser_token_headers,
        )
        assert res_put.status_code == 200
        assert res_put.json()["name"] == "Audífonos Bluetooth Pro"
        assert res_put.json()["cover_image_url"] == mock_resp["url"]

        # 5. DELETE /api/commerce/product-masters/{id}/images/{image_id}
        res_del = client.delete(
            f"/api/commerce/product-masters/{master.id}/images/{img_id}",
            headers=superuser_token_headers,
        )
        assert res_del.status_code == 200
        assert res_del.json()["message"] == "Fotografía eliminada exitosamente"

        # Verificar que ya no hay imágenes
        res_empty = client.get(
            f"/api/commerce/product-masters/{master.id}/images",
            headers=superuser_token_headers,
        )
        assert res_empty.status_code == 200
        assert len(res_empty.json()) == 0


def test_detect_portal_classification():
    portal, label = detect_portal(
        "https://www.amazon.co.uk/Fitabok-Electric-Heater-Portable-Protection/dp/B0FJ8GPS3J"
    )
    assert portal == "AMAZON"
    assert label == "Amazon UK"

    portal, label = detect_portal("https://www.amazon.es/dp/B08XJ8P9W9")
    assert portal == "AMAZON"
    assert label == "Amazon España"

    portal, label = detect_portal("https://www.ebay.com/itm/123456789")
    assert portal == "EBAY"
    assert label == "eBay"

    portal, label = detect_portal("https://es.aliexpress.com/item/100500123.html")
    assert portal == "ALIEXPRESS"
    assert label == "AliExpress"

    portal, label = detect_portal("https://spanish.alibaba.com/p-detail/sample.html")
    assert portal == "ALIBABA"
    assert label == "Alibaba"

    portal, label = detect_portal("https://www.walmart.com/ip/seort/123456")
    assert portal == "WALMART"
    assert label == "Walmart"

    portal, label = detect_portal("https://articulo.mercadolibre.com.bo/MLC-123")
    assert portal == "MERCADOLIBRE"
    assert label == "MercadoLibre"

    portal, label = detect_portal("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert portal == "YOUTUBE"
    assert label == "YouTube"

    portal, label = detect_portal("https://www.tiktok.com/@user/video/12345")
    assert portal == "TIKTOK"
    assert label == "TikTok"

    portal, label = detect_portal("https://sifsof.com/product/sphygmomanometer")
    assert portal == "OTHER"
    assert label == "Sifsof"


def test_product_master_external_links_service(session: Session):
    service = ProductMasterService(session)

    # 1. Crear ficha con initial_external_url -> crea enlace automáticamente
    master = service.create(
        ProductMaster(
            name="Calefactor Fitabok",
            official_price=250.0,
            minimum_price=200.0,
        ),
        initial_external_url="https://www.amazon.co.uk/dp/B0FJ8GPS3J",
    )

    links = service.get_external_links(master.id)
    assert len(links) == 1
    assert links[0].portal == "AMAZON"
    assert links[0].label == "Amazon UK"
    assert links[0].is_primary is True
    assert links[0].is_public is True
    assert links[0].sort_order == 1

    # 2. Agregar segundo enlace privado (Alibaba)
    alibaba_link = service.add_external_link(
        master_id=master.id,
        url="https://spanish.alibaba.com/p-detail/12345.html",
        label=None,  # auto-detect
        is_public=False,
    )
    assert alibaba_link.portal == "ALIBABA"
    assert alibaba_link.label == "Alibaba"
    assert alibaba_link.is_primary is False
    assert alibaba_link.is_public is False
    assert alibaba_link.sort_order == 2

    # Verificar filtro only_public
    public_links = service.get_external_links(master.id, only_public=True)
    assert len(public_links) == 1
    assert public_links[0].portal == "AMAZON"

    # 3. Cambiar Alibaba como enlace principal
    service.set_primary_external_link(master.id, alibaba_link.id)
    links_after_primary = service.get_external_links(master.id)
    primary_link = next(lnk for lnk in links_after_primary if lnk.is_primary)
    assert primary_link.id == alibaba_link.id

    # 4. Eliminar el enlace primario (Alibaba) -> promueve el siguiente (Amazon)
    service.delete_external_link(master.id, alibaba_link.id)
    remaining_links = service.get_external_links(master.id)
    assert len(remaining_links) == 1
    assert remaining_links[0].is_primary is True
    assert remaining_links[0].portal == "AMAZON"

    # 5. Eliminar último enlace -> sin enlaces
    service.delete_external_link(master.id, remaining_links[0].id)
    assert len(service.get_external_links(master.id)) == 0


def test_product_master_external_links_api(
    client: TestClient, superuser_token_headers: dict, session: Session
):
    service = ProductMasterService(session)
    master = service.create(
        ProductMaster(
            name="Proyector TP360",
            official_price=450.0,
            minimum_price=380.0,
        )
    )

    # 1. POST /api/commerce/product-masters/{id}/links (Amazon)
    res_add1 = client.post(
        f"/api/commerce/product-masters/{master.id}/links",
        json={
            "url": "https://www.amazon.es/dp/B00123456",
            "label": "Ficha Amazon España",
        },
        headers=superuser_token_headers,
    )
    assert res_add1.status_code == 200
    link1 = res_add1.json()
    assert link1["portal"] == "AMAZON"
    assert link1["label"] == "Ficha Amazon España"
    assert link1["is_primary"] is True
    link1_id = link1["id"]

    # 2. POST /api/commerce/product-masters/{id}/links (Alibaba sin label -> auto)
    res_add2 = client.post(
        f"/api/commerce/product-masters/{master.id}/links",
        json={"url": "https://spanish.alibaba.com/p-detail/projector-tp360.html"},
        headers=superuser_token_headers,
    )
    assert res_add2.status_code == 200
    link2 = res_add2.json()
    assert link2["portal"] == "ALIBABA"
    assert link2["label"] == "Alibaba"
    assert link2["is_primary"] is False
    link2_id = link2["id"]

    # 3. GET /api/commerce/product-masters/{id} verifica external_links y count
    res_master = client.get(
        f"/api/commerce/product-masters/{master.id}",
        headers=superuser_token_headers,
    )
    assert res_master.status_code == 200
    master_data = res_master.json()
    assert master_data["external_links_count"] == 2
    assert len(master_data["external_links"]) == 2
    assert master_data["external_info_url"] == "https://www.amazon.es/dp/B00123456"

    # 4. PATCH /api/commerce/product-masters/{id}/links/{link_id}/primary
    res_primary = client.patch(
        f"/api/commerce/product-masters/{master.id}/links/{link2_id}/primary",
        headers=superuser_token_headers,
    )
    assert res_primary.status_code == 200
    assert res_primary.json()["is_primary"] is True

    # 4.b Verificar que external_info_url ahora refleje el nuevo enlace primario
    res_master2 = client.get(
        f"/api/commerce/product-masters/{master.id}",
        headers=superuser_token_headers,
    )
    assert res_master2.status_code == 200
    assert res_master2.json()["external_info_url"] == link2["url"]

    # 4.c Modificar is_public a false vía PATCH
    res_patch_priv = client.patch(
        f"/api/commerce/product-masters/{master.id}/links/{link2_id}",
        json={"is_public": False},
        headers=superuser_token_headers,
    )
    assert res_patch_priv.status_code == 200
    assert res_patch_priv.json()["is_public"] is False

    # 4.d GET con ?only_public=true
    res_pub_only = client.get(
        f"/api/commerce/product-masters/{master.id}/links?only_public=true",
        headers=superuser_token_headers,
    )
    assert res_pub_only.status_code == 200
    pub_links = res_pub_only.json()
    assert len(pub_links) == 1
    assert pub_links[0]["id"] == link1_id

    # 5. PUT /api/commerce/product-masters/{id}/links/reorder
    res_reorder = client.put(
        f"/api/commerce/product-masters/{master.id}/links/reorder",
        json=[{"id": link2_id, "sort_order": 1}, {"id": link1_id, "sort_order": 2}],
        headers=superuser_token_headers,
    )
    assert res_reorder.status_code == 200
    reordered = res_reorder.json()
    assert reordered[0]["id"] == link2_id

    # 6. DELETE /api/commerce/product-masters/{id}/links/{link_id}
    res_del = client.delete(
        f"/api/commerce/product-masters/{master.id}/links/{link2_id}",
        headers=superuser_token_headers,
    )
    assert res_del.status_code == 200
    assert res_del.json()["message"] == "Enlace externo eliminado exitosamente"

    # 7. MARKETPLACE Links: Múltiples publicaciones ("Liz y Henry")
    # 7.a Añadir publicación de Marketplace de Liz
    res_mkt1 = client.post(
        f"/api/commerce/product-masters/{master.id}/links",
        json={
            "url": "https://www.facebook.com/marketplace/item/999111/",
            "link_type": "MARKETPLACE",
            "label": "Marketplace - Liz (La Paz)",
        },
        headers=superuser_token_headers,
    )
    assert res_mkt1.status_code == 200
    mkt1 = res_mkt1.json()
    assert mkt1["link_type"] == "MARKETPLACE"
    assert mkt1["portal"] == "FACEBOOK"
    assert mkt1["label"] == "Marketplace - Liz (La Paz)"
    assert mkt1["is_primary"] is True

    # 7.b Añadir publicación de Marketplace de Henry
    res_mkt2 = client.post(
        f"/api/commerce/product-masters/{master.id}/links",
        json={
            "url": "https://www.facebook.com/marketplace/item/888222/",
            "link_type": "MARKETPLACE",
            "label": "Marketplace - Henry (Central)",
        },
        headers=superuser_token_headers,
    )
    assert res_mkt2.status_code == 200
    mkt2 = res_mkt2.json()
    assert mkt2["link_type"] == "MARKETPLACE"
    assert mkt2["is_primary"] is False

    # 7.c Verificar que la ficha maestra refleja marketplace y reference links
    res_master3 = client.get(
        f"/api/commerce/product-masters/{master.id}",
        headers=superuser_token_headers,
    )
    assert res_master3.status_code == 200
    m_data3 = res_master3.json()
    assert m_data3["is_published_marketplace"] is True
    assert (
        m_data3["marketplace_url"]
        == "https://www.facebook.com/marketplace/item/999111/"
    )
    assert m_data3["external_info_url"] == "https://www.amazon.es/dp/B00123456"
    assert m_data3["reference_links_count"] == 1
    assert m_data3["marketplace_links_count"] == 2
    assert len(m_data3["marketplace_links"]) == 2

    # 7.d Filtrar links por link_type=MARKETPLACE
    res_filter_mkt = client.get(
        f"/api/commerce/product-masters/{master.id}/links?link_type=MARKETPLACE",
        headers=superuser_token_headers,
    )
    assert res_filter_mkt.status_code == 200
    mkt_only = res_filter_mkt.json()
    assert len(mkt_only) == 2
    assert all(lnk["link_type"] == "MARKETPLACE" for lnk in mkt_only)

    # 7.e Fijar mkt2 como primario no debe desmarcar el primario de REFERENCE
    res_mkt2_pri = client.patch(
        f"/api/commerce/product-masters/{master.id}/links/{mkt2['id']}/primary",
        headers=superuser_token_headers,
    )
    assert res_mkt2_pri.status_code == 200
    assert res_mkt2_pri.json()["is_primary"] is True

    res_master4 = client.get(
        f"/api/commerce/product-masters/{master.id}",
        headers=superuser_token_headers,
    )
    m_data4 = res_master4.json()
    assert (
        m_data4["marketplace_url"]
        == "https://www.facebook.com/marketplace/item/888222/"
    )
    assert m_data4["external_info_url"] == "https://www.amazon.es/dp/B00123456"


def test_investment_round_and_batch_costing_modalities(
    client, superuser_token_headers, session: Session
):
    from app.modules.commerce.batches.service import BatchService
    from app.modules.commerce.products.service import ProductService
    from app.modules.commerce.rounds.models import InvestmentRound
    from app.modules.commerce.rounds.service import InvestmentRoundService
    from app.modules.commerce.sales.schemas import SaleCreate, SaleItemCreate
    from app.modules.commerce.sales.service import SaleService

    round_service = InvestmentRoundService(session)
    batch_service = BatchService(session)
    product_service = ProductService(session)
    sale_service = SaleService(session)

    # 1. Crear Ronda de Inversión 04 con capital inicial 0.0
    ronda = round_service.create(
        InvestmentRound(
            code="RONDA-04-TEST",
            name="Ronda 4 (Campaña Fin de Año)",
            capital_invested=0.0,
            status="ACTIVE",
        )
    )
    assert ronda.capital_invested == 0.0
    assert ronda.status == "ACTIVE"

    # Verificar métricas iniciales
    res_m = client.get(
        f"/api/commerce/rounds/{ronda.id}/metrics",
        headers=superuser_token_headers,
    )
    assert res_m.status_code == 200
    metrics = res_m.json()
    assert metrics["capital_invested"] == 0.0
    assert metrics["batches_count"] == 0

    # 2. Opción 1: Caja Amazon Mixta (WEIGHTED_RETAIL)
    # Lote cerrado de 2000 Bs (compra 1800 + flete 200)
    batch_liq = batch_service.create(
        Batch(
            code="AMZ-BOX-2026",
            name="Caja Amazon Liquidación",
            investment_round_id=ronda.id,
            costing_method="WEIGHTED_RETAIL",
            purchase_price=1800.0,
            freight_cost=200.0,
        )
    )
    assert batch_liq.total_cost == 2000.0

    # La ronda debe haber actualizado automáticamente su capital_invested a 2000.0
    ronda_refreshed = round_service.get_by_id(ronda.id)
    assert ronda_refreshed is not None
    assert ronda_refreshed.capital_invested == 2000.0

    # Añadir productos a la caja de liquidación
    m_radio = make_master(
        session,
        301,
        "Radio Pantalla Car",
        published_price=700.0,
        official_price=800.0,
        minimum_price=500.0,
    )
    m_cable = make_master(
        session,
        302,
        "Cable USB C",
        published_price=30.0,
        official_price=35.0,
        minimum_price=20.0,
    )
    m_merma = make_master(
        session,
        303,
        "Foco Roto",
        published_price=50.0,
        official_price=50.0,
        minimum_price=20.0,
    )

    p_radio = product_service.create(
        Product(
            master_product_id=m_radio.id,
            batch_id=batch_liq.id,
            initial_quantity=1,
        )
    )
    p_cable = product_service.create(
        Product(
            master_product_id=m_cable.id,
            batch_id=batch_liq.id,
            initial_quantity=10,
        )
    )
    # Añadir merma física
    product_service.create(
        Product(
            master_product_id=m_merma.id,
            batch_id=batch_liq.id,
            initial_quantity=1,
            merma_quantity=1,
            physical_condition="DAMAGED_SCRAP",
        )
    )

    # Ejecutar prorrateo ponderado por valor comercial (published_price)
    batch_alloc = batch_service.allocate_relative_costs(
        batch_liq.id, basis="published_price"
    )
    assert batch_alloc is not None

    p_radio_up = product_service.get_by_id(p_radio.id)
    p_cable_up = product_service.get_by_id(p_cable.id)
    assert p_radio_up is not None and p_cable_up is not None
    # Valor base: Radio = 700 * 1 = 700; Cable = 30 * 10 = 300. Total = 1000.
    # Factor de costo = 2000 / 1000 = 2.0
    # Costo Radio = 700 * 2.0 = 1400.0
    # Costo Cable unitario = 30 * 2.0 = 60.0
    # Cuadre: 1400.0 * 1 + 60.0 * 10 = 2000.0 (exacto a batch_liq.total_cost)
    assert p_radio_up.cost_price == 1400.0
    assert p_cable_up.cost_price == 60.0

    # 3. Opción 2: Reposición Bajo Demanda (SPECIFIC_ITEM / Bottom-Up)
    batch_spot = batch_service.create(
        Batch(
            code="SPOT-REORDER-01",
            name="Reposición a Pedido",
            investment_round_id=ronda.id,
            costing_method="SPECIFIC_ITEM",
            purchase_price=0.0,
            freight_cost=50.0,
        )
    )
    m_taladro = make_master(
        session,
        304,
        "Taladro Pro",
        published_price=350.0,
        minimum_price=300.0,
    )
    p_taladro = product_service.create(
        Product(
            master_product_id=m_taladro.id,
            batch_id=batch_spot.id,
            initial_quantity=2,
            cost_price=100.0,  # Comprado a 100 Bs c/u
        )
    )
    # Lote de reposición debe calcular automáticamente:
    # purchase_price = 2 * 100 = 200.0
    # total_cost = 200 + 50 (flete) = 250.0
    # unit_cost = 250 / 2 = 125.0
    batch_spot_up = batch_service.get_by_id(batch_spot.id)
    assert batch_spot_up is not None
    assert batch_spot_up.purchase_price == 200.0
    assert batch_spot_up.total_cost == 250.0
    assert batch_spot_up.unit_cost == 125.0

    # Y la ronda debe sumar ambos lotes: 2000 + 250 = 2250.0
    ronda_both = round_service.get_by_id(ronda.id)
    assert ronda_both is not None
    assert ronda_both.capital_invested == 2250.0

    # 4. Registrar Ventas y Verificar Break-Even
    # Venta de Radio a 700 Bs
    sale_service.create(
        SaleCreate(
            customer_name="Cliente A",
            channel="Marketplace",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[SaleItemCreate(product_id=p_radio.id, quantity=1, unit_price=700.0)],
        )
    )
    # Venta de 2 Taladros a 350 Bs c/u (700 Bs)
    sale_service.create(
        SaleCreate(
            customer_name="Cliente B",
            channel="WhatsApp",
            payment_method="Efectivo",
            payment_status="COLLECTED",
            items=[
                SaleItemCreate(product_id=p_taladro.id, quantity=2, unit_price=350.0)
            ],
        )
    )

    # Métricas de ronda tras 1400 Bs recuperados (1400 / 2250 = ~62.22%)
    res_m2 = client.get(
        f"/api/commerce/rounds/{ronda.id}/metrics",
        headers=superuser_token_headers,
    )
    assert res_m2.status_code == 200
    m2 = res_m2.json()
    assert m2["capital_invested"] == 2250.0
    assert m2["capital_recovered"] == 1400.0
    assert m2["is_break_even"] is False
    assert m2["status"] == "IN_RECOVERY"

    # Venta restante de 10 cables a 90 Bs c/u (900 Bs) -> Total = 1400 + 900 = 2300 Bs
    sale_service.create(
        SaleCreate(
            customer_name="Cliente Mayorista",
            channel="Marketplace",
            payment_method="QR",
            payment_status="COLLECTED",
            items=[SaleItemCreate(product_id=p_cable.id, quantity=10, unit_price=90.0)],
        )
    )

    # Ahora capital_recovered (2300) > capital_invested (2250): BREAK-EVEN ALCANZADO
    res_m3 = client.get(
        f"/api/commerce/rounds/{ronda.id}/metrics",
        headers=superuser_token_headers,
    )
    assert res_m3.status_code == 200
    m3 = res_m3.json()
    assert m3["capital_recovered"] == 2300.0
    assert m3["net_profit"] == 50.0
    assert m3["is_break_even"] is True
    assert m3["available_items"] == 0  # Todo vendido
    assert m3["status"] == "LIQUIDATED"


def test_personal_used_items_consignment_and_handmade_flow(
    session: Session, client: TestClient, superuser_token_headers: dict
):
    round_service = InvestmentRoundService(session)
    batch_service = BatchService(session)
    product_service = ProductService(session)
    sale_service = SaleService(session)

    # 1. Crear Ronda de Inversión abierta (Bazar y Artesanías)
    ronda = round_service.create(
        InvestmentRound(
            code="RND-BAZAR",
            name="Ronda Bazar y Manufacturas",
            capital_invested=0.0,
            status="ACTIVE",
        )
    )

    # 2. Crear Lote dinámico sin costo inicial de compra (0 Bs inicial)
    batch = batch_service.create(
        Batch(
            name="Lote Bazar Cosas Usadas y Artesanías",
            code="LOT-BAZAR-01",
            costing_method="SPECIFIC_ITEM",
            purchase_price=0.0,
            freight_cost=0.0,
            initial_items_count=0,
            investment_round_id=ronda.id,
        )
    )
    assert batch.purchase_price == 0.0
    assert batch.total_cost == 0.0
    assert batch.initial_items_count == 0

    # Tanda 1: Cosas Propias de Socios (Costo Cero / Ganancia Pura)
    m_propia = make_master(
        session,
        101,
        "Chaqueta Cuero Usada (Propia)",
        official_price=150.0,
        published_price=120.0,
        minimum_price=100.0,
    )
    p_propia = product_service.create(
        Product(
            master_product_id=m_propia.id,
            batch_id=batch.id,
            cost_price=0.0,
            initial_quantity=1,
        )
    )
    b_step1 = batch_service.get_by_id(batch.id)
    assert b_step1.initial_items_count == 1
    assert b_step1.total_cost == 0.0  # Sin deuda ni capital comprometido

    # Tanda 2: Consignación de Familiar (Pago acordado al vender)
    m_primo = make_master(
        session,
        102,
        "Bicicleta Montaña (Consignación Primo)",
        official_price=400.0,
        published_price=350.0,
        minimum_price=300.0,
    )
    p_primo = product_service.create(
        Product(
            master_product_id=m_primo.id,
            batch_id=batch.id,
            cost_price=200.0,  # Pago comprometido para el familiar
            initial_quantity=1,
        )
    )
    b_step2 = batch_service.get_by_id(batch.id)
    assert b_step2.initial_items_count == 2
    assert b_step2.purchase_price == 200.0  # Sumó la obligación del ítem
    assert b_step2.total_cost == 200.0

    # Tanda 3: Producto Hecho a Mano / Artesanías (Costo de insumos y materiales)
    m_artesania = make_master(
        session,
        103,
        "Arreglo Floral Navideño Hecho a Mano",
        official_price=100.0,
        published_price=90.0,
        minimum_price=75.0,
    )
    p_artesania = product_service.create(
        Product(
            master_product_id=m_artesania.id,
            batch_id=batch.id,
            cost_price=30.0,  # Materiales (flores, cintas, base)
            initial_quantity=1,
        )
    )
    b_step3 = batch_service.get_by_id(batch.id)
    assert b_step3.initial_items_count == 3
    assert b_step3.purchase_price == 230.0  # 200 + 30
    assert b_step3.total_cost == 230.0

    # 3. Venta 1: Chaqueta Propia vendida en 110 Bs
    # Al ser costo 0, la ganancia neta es el 100% del ingreso (110 Bs)
    s1 = sale_service.create(
        SaleCreate(
            customer_name="Cliente Usados 1",
            channel="Marketplace",
            items=[
                SaleItemCreate(product_id=p_propia.id, quantity=1, unit_price=110.0)
            ],
        )
    )
    assert s1.total_collected == 110.0
    assert s1.total_cost == 0.0
    assert s1.net_profit == 110.0

    # 4. Venta 2: Bicicleta en Consignación vendida en 320 Bs
    # Cobrado: 320 Bs, Costo (pago al familiar): 200 Bs, Ganancia Uyuni: 120 Bs
    s2 = sale_service.create(
        SaleCreate(
            customer_name="Cliente Usados 2",
            channel="Facebook",
            items=[SaleItemCreate(product_id=p_primo.id, quantity=1, unit_price=320.0)],
        )
    )
    assert s2.total_collected == 320.0
    assert s2.total_cost == 200.0
    assert s2.net_profit == 120.0

    # 5. Venta 3: Arreglo Hecho a Mano vendido en 85 Bs
    # Cobrado: 85 Bs, Insumos: 30 Bs, Ganancia: 55 Bs
    s3 = sale_service.create(
        SaleCreate(
            customer_name="Cliente Navidad",
            channel="Local",
            items=[
                SaleItemCreate(product_id=p_artesania.id, quantity=1, unit_price=85.0)
            ],
        )
    )
    assert s3.total_collected == 85.0
    assert s3.total_cost == 30.0
    assert s3.net_profit == 55.0

    # 6. Consultar métricas de la Ronda vía API
    res_m = client.get(
        f"/api/commerce/rounds/{ronda.id}/metrics",
        headers=superuser_token_headers,
    )
    assert res_m.status_code == 200
    m = res_m.json()
    # Total invertido/comprometido: 230 Bs (0 propia + 200 primo + 30 materiales)
    assert m["capital_invested"] == 230.0
    # Total recaudado: 110 + 320 + 85 = 515 Bs
    assert m["capital_recovered"] == 515.0
    # Ganancia neta: 515 - 230 = 285 Bs
    assert m["net_profit"] == 285.0
    assert m["available_items"] == 0
    assert m["sold_items"] == 3
    assert m["is_break_even"] is True
    assert m["status"] == "LIQUIDATED"


def test_delete_investment_round_integrity(
    session: Session, client: TestClient, superuser_token_headers: dict
):
    round_service = InvestmentRoundService(session)
    batch_service = BatchService(session)

    # 1. Ronda sin lotes asociados: debe permitir eliminar limpiamente
    ronda_vacia = round_service.create(
        InvestmentRound(
            code="RND-EMPTY",
            name="Ronda de Prueba Vacía",
            capital_invested=0.0,
            status="ACTIVE",
        )
    )
    res_del_ok = client.delete(
        f"/api/commerce/rounds/{ronda_vacia.id}",
        headers=superuser_token_headers,
    )
    assert res_del_ok.status_code == 200
    assert "deleted successfully" in res_del_ok.json()["message"]
    assert round_service.get_by_id(ronda_vacia.id) is None

    # 2. Ronda con lotes asociados: debe rechazar la eliminación (HTTP 400)
    ronda_con_lote = round_service.create(
        InvestmentRound(
            code="RND-WITH-BATCH",
            name="Ronda con Lotes Asociados",
            capital_invested=500.0,
            status="ACTIVE",
        )
    )
    batch = batch_service.create(
        Batch(
            code="BATCH-RND-TEST",
            name="Lote Asociado a Ronda",
            investment_round_id=ronda_con_lote.id,
            purchase_price=500.0,
        )
    )

    res_del_blocked = client.delete(
        f"/api/commerce/rounds/{ronda_con_lote.id}",
        headers=superuser_token_headers,
    )
    assert res_del_blocked.status_code == 400
    detail = res_del_blocked.json()["detail"]
    assert "No se puede eliminar la ronda" in detail
    assert "1 lote(s) asociado(s)" in detail

    # 3. Desvincular el lote y reintentar eliminar: ahora sí debe permitir
    batch_service.update(batch.id, {"investment_round_id": None})
    res_del_after_unlink = client.delete(
        f"/api/commerce/rounds/{ronda_con_lote.id}",
        headers=superuser_token_headers,
    )
    assert res_del_after_unlink.status_code == 200
    assert round_service.get_by_id(ronda_con_lote.id) is None

