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
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.service import ProductMasterService
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

    # 3. Create Product Master via API
    res_master = client.post(
        "/api/commerce/product-masters/",
        headers=superuser_token_headers,
        json={
            "item_number": 53,
            "name": "Almohadilla Térmica API",
            "official_price": 250.0,
            "minimum_price": 200.0,
        },
    )
    assert res_master.status_code == 200
    master_id = res_master.json()["id"]

    res_master_num = client.get(
        "/api/commerce/product-masters/by-number/53",
        headers=superuser_token_headers,
    )
    assert res_master_num.status_code == 200
    assert res_master_num.json()["id"] == master_id

    res_master_res = client.get(
        "/api/commerce/product-masters/resolve/NOV-053",
        headers=superuser_token_headers,
    )
    assert res_master_res.status_code == 200
    assert res_master_res.json()["item_number"] == 53

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
            marketplace_url="https://facebook.com/marketplace/item/123",
            is_published_marketplace=True,
            is_whatsapp_published=True,
            is_fb_verified=True,
        )
    )
    assert master.id is not None
    assert master.item_number == 53
    assert master.code == "53"
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
