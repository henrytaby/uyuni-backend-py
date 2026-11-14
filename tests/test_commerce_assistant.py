from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.modules.commerce.assistant.provider import (
    call_llm,
)
from app.modules.commerce.assistant.service import CommerceAssistantService
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.service import ProductMasterService
from app.modules.commerce.products.models import Product
from app.modules.commerce.products.service import ProductService


def test_extract_search_terms():
    service = CommerceAssistantService(MagicMock())
    query = "¿Cuántos cargadores de celulares tenemos en stock para venta?"
    terms = service.extract_search_terms(query)
    assert "cargadores" in terms
    assert "celulares" in terms
    assert "cuantos" not in terms
    assert "stock" not in terms
    assert "tenemos" not in terms


def test_inventory_search_and_summary(session: Session):
    master_svc = ProductMasterService(session)
    product_svc = ProductService(session)

    # 1. Crear Ficha Maestra
    master = master_svc.create(
        ProductMaster(
            item_number=88,
            name="Cargador Rápido 30W Baseus",
            brand="Baseus",
            model="Speed Mini",
            features="Carga rápida USB-C y USB-A, compatible con iPhone y Android",
            official_price=55.0,
            published_price=50.0,
            minimum_price=45.0,
        )
    )

    # 2. Asignar inventario físico
    product_svc.create(
        Product(
            master_product_id=master.id,
            initial_quantity=21,
            sold_quantity=5,
            merma_quantity=1,
            cost_price=25.0,
        )
    )

    assistant_svc = CommerceAssistantService(session)

    # Resumen global
    summary = assistant_svc.get_global_inventory_summary()
    assert summary["total_product_masters"] >= 1
    assert summary["total_available_units"] >= 15

    # Búsqueda por término
    matched = assistant_svc.search_relevant_products("cargador baseus")
    assert len(matched) >= 1
    target = next((p for p in matched if p.item_number == 88), None)
    assert target is not None
    assert target.name == "Cargador Rápido 30W Baseus"
    assert target.available_stock == 15
    assert target.sold_stock == 5
    assert target.official_price == 55.0
    assert target.published_price == 50.0


def test_build_system_prompt(session: Session):
    assistant_svc = CommerceAssistantService(session)
    matched = assistant_svc.search_relevant_products("cargador")
    summary = assistant_svc.get_global_inventory_summary()

    prompt = assistant_svc.build_system_prompt(matched, summary)
    assert "Inventario y Ventas" in prompt
    assert "DATOS DE INVENTARIO EN TIEMPO REAL:" in prompt
    assert "REGLAS DE ORO DE INVENTARIO" in prompt


def test_call_llm_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Tenemos 15 cargadores Baseus en stock.",
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp

    with (
        patch("httpx2.Client", return_value=mock_client),
        patch.object(settings, "GROQ_API_KEY", "gsk_test_key_12345"),
    ):
        reply, provider, model, fallback = call_llm(
            messages=[{"role": "user", "content": "¿Tienen cargador?"}],
            requested_provider="groq",
        )

        assert reply == "Tenemos 15 cargadores Baseus en stock."
        assert provider == "groq"
        assert fallback is False


def test_call_llm_fallback():
    # Primer proveedor (Groq) falla con 503 Overloaded
    groq_resp = MagicMock()
    groq_resp.status_code = 503
    groq_resp.text = "Model is overloaded"

    # Segundo proveedor (Mistral) responde 200 OK
    mistral_resp = MagicMock()
    mistral_resp.status_code = 200
    mistral_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Respuesta desde Mistral Fallback.",
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.side_effect = [groq_resp, mistral_resp]

    with (
        patch("httpx2.Client", return_value=mock_client),
        patch.object(settings, "GROQ_API_KEY", "gsk_groq_key"),
        patch.object(settings, "MISTRAL_API_KEY", "mis_mistral_key"),
        patch.object(settings, "AI_ENABLE_FALLBACK", True),
    ):
        reply, provider, model, fallback = call_llm(
            messages=[{"role": "user", "content": "¿Hay stock?"}],
            requested_provider="groq",
        )

        assert reply == "Respuesta desde Mistral Fallback."
        assert provider == "mistral"
        assert fallback is True


def test_call_llm_invalid_provider():
    try:
        call_llm(
            messages=[{"role": "user", "content": "hola"}],
            requested_provider="proveedor_fantasma",
        )
        pytest.fail("Debe lanzar BadRequestException")
    except BadRequestException as exc:
        assert "no soportado" in str(exc)


def test_assistant_api_endpoints(client: TestClient, superuser_token_headers):
    # 1. GET /api/commerce/assistant/providers
    with patch.object(settings, "GROQ_API_KEY", "gsk_active_key"):
        resp = client.get(
            "/api/commerce/assistant/providers",
            headers=superuser_token_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "default_provider" in data
        assert "configured_providers" in data
        assert "all_providers" in data
        assert "groq" in data["all_providers"]
        assert "mistral" in data["all_providers"]
        assert "gemini" in data["all_providers"]

    # 2. POST /api/commerce/assistant/chat con mock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Sí, tenemos 12 cargadores disponibles.",
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp

    with (
        patch("httpx2.Client", return_value=mock_client),
        patch.object(settings, "GROQ_API_KEY", "gsk_mock_key"),
    ):
        chat_req = {
            "message": "¿Tenemos cargadores?",
            "provider": "groq",
            "history": [],
        }
        res = client.post(
            "/api/commerce/assistant/chat",
            json=chat_req,
            headers=superuser_token_headers,
        )
        assert res.status_code == 200
        chat_data = res.json()
        assert chat_data["reply"] == "Sí, tenemos 12 cargadores disponibles."
        assert chat_data["provider_used"] == "groq"
        assert "matched_products" in chat_data


def test_assistant_api_no_keys_configured(client: TestClient, superuser_token_headers):
    # Sin ninguna key configurada debe retornar 400 informando que faltan keys en .env
    with (
        patch.object(settings, "GROQ_API_KEY", None),
        patch.object(settings, "MISTRAL_API_KEY", None),
        patch.object(settings, "GEMINI_API_KEY", None),
    ):
        res = client.post(
            "/api/commerce/assistant/chat",
            json={"message": "¿Hay stock?"},
            headers=superuser_token_headers,
        )
        assert res.status_code == 400
        assert "No se ha configurado ninguna API Key" in res.json()["detail"]


def test_detect_query_intent():
    service = CommerceAssistantService(MagicMock())

    # 1. Consulta explícita por disponibilidad
    intent1 = service.detect_query_intent("¿Tenemos proyector disponibles?")
    assert intent1["wants_available_only"] is True
    assert intent1["wants_all"] is False

    # 2. Consulta por todo el catálogo
    intent2 = service.detect_query_intent(
        "Muéstrame todos los proyectores del catálogo"
    )
    assert intent2["wants_all"] is True
    assert intent2["wants_available_only"] is False

    # 3. Consulta general sin especificación
    intent3 = service.detect_query_intent("proyector #140")
    assert intent3["wants_all"] is False
    assert intent3["wants_available_only"] is False


def test_extract_item_numbers():
    service = CommerceAssistantService(MagicMock())
    assert service.extract_item_numbers("proyector #140") == [140]
    assert service.extract_item_numbers("item 222 y #54") == [222, 54]
    assert service.extract_item_numbers("¿tienen cargadores?") == []


def test_stop_words_exclude_disponibles_and_stock():
    service = CommerceAssistantService(MagicMock())
    terms = service.extract_search_terms("¿Tenemos proyector disponibles en stock?")
    assert terms == ["proyector"]


def test_intent_aware_product_filtering(session: Session):
    master_svc = ProductMasterService(session)
    product_svc = ProductService(session)

    # 1. Proyector con stock disponible
    p1 = master_svc.create(
        ProductMaster(
            item_number=501,
            name="Proyector Wielio 4K",
            official_price=750.0,
            minimum_price=500.0,
        )
    )
    product_svc.create(
        Product(
            master_product_id=p1.id,
            initial_quantity=5,
            sold_quantity=0,
            cost_price=300.0,
        )
    )

    # 2. Proyector agotado (Stock 0)
    master_svc.create(
        ProductMaster(
            item_number=502,
            name="Proyector Astronauta Estrellas",
            official_price=140.0,
            minimum_price=110.0,
        )
    )

    assistant_svc = CommerceAssistantService(session)

    # Simular handle_chat cuando se pide "disponibles"
    with patch(
        "app.modules.commerce.assistant.service.call_llm",
        return_value=("Respuesta LLM", "groq", "test-model", False),
    ):
        from app.modules.commerce.assistant.schemas import ChatAssistantRequest

        req = ChatAssistantRequest(message="¿Tenemos proyector disponibles?")
        resp = assistant_svc.handle_chat(req)

        # Para las tarjetas en la UI, solo debe devolver el disponible #501
        assert len(resp.matched_products) == 1
        assert resp.matched_products[0].item_number == 501
        assert resp.matched_products[0].available_stock == 5

        # Cuando se pide "todos", debe devolver ambos (#501 y #502)
        req_all = ChatAssistantRequest(message="Muéstrame todos los proyectores")
        resp_all = assistant_svc.handle_chat(req_all)
        assert len(resp_all.matched_products) == 2


def test_general_stock_query_brings_only_available_products(session: Session):
    master_svc = ProductMasterService(session)
    product_svc = ProductService(session)

    # Crear 3 productos con stock y 3 sin stock
    for i in range(1, 4):
        m = master_svc.create(
            ProductMaster(
                item_number=700 + i,
                name=f"Producto Con Stock {i}",
                official_price=100.0,
                minimum_price=80.0,
            )
        )
        product_svc.create(
            Product(
                master_product_id=m.id,
                initial_quantity=10,
                sold_quantity=2,
                cost_price=50.0,
            )
        )

    for i in range(4, 7):
        master_svc.create(
            ProductMaster(
                item_number=700 + i,
                name=f"Producto Agotado {i}",
                official_price=100.0,
                minimum_price=80.0,
            )
        )

    assistant_svc = CommerceAssistantService(session)
    # Búsqueda general de stock
    matched = assistant_svc.search_relevant_products(
        "¿Qué productos tienen unidades disponibles en stock hoy?", limit=10
    )
    # Debe traer los que tengan stock y ninguno de los agotados
    assert all(p.available_stock > 0 for p in matched)
    item_nums = [p.item_number for p in matched]
    assert 701 in item_nums
    assert 702 in item_nums
    assert 703 in item_nums
    assert 704 not in item_nums
    assert 705 not in item_nums
    assert 706 not in item_nums


def test_keyword_validation_auto_discards_automatico():
    service = CommerceAssistantService(MagicMock())
    p_fairy = ProductMaster(
        name="Guirnalda de Luces Hada LED",
        features="8 modos de iluminación y ciclo automático 6h",
    )
    p_radio = ProductMaster(
        name="Radio Pantalla Android Auto 7 pulgadas",
        features="Car Stereo para auto con Bluetooth",
    )
    assert service._is_valid_keyword_match("auto", p_fairy) is False
    assert service._is_valid_keyword_match("auto", p_radio) is True


def test_extract_cited_item_numbers():
    service = CommerceAssistantService(MagicMock())
    reply = """
    | Catálogo # | Producto | Stock | Precio |
    | 235 | Radio Android Auto | 1 | 700.00 |
    | 203 | Refractómetro | 1 | 180.00 |
    """
    candidates = {235, 203, 211, 240, 700, 180}
    cited = service.extract_cited_item_numbers(reply, candidates)
    assert cited == {235, 203}
    assert 700 not in cited  # El precio no debe confundirse con un ID de catálogo
    assert 180 not in cited


def test_synonym_expansion_and_typo_item_numbers(session: Session):
    master_svc = ProductMasterService(session)
    product_svc = ProductService(session)

    # 1. Producto que NO tiene la palabra "auto", pero dice "vehículo" y "coche"
    p_vehiculo = master_svc.create(
        ProductMaster(
            item_number=888,
            name="Soporte Magnético para Parabrisas de Vehículo",
            brand="Baseus",
            features="Compatible con cualquier coche o camioneta",
            official_price=120.0,
            minimum_price=90.0,
        )
    )
    product_svc.create(
        Product(
            master_product_id=p_vehiculo.id,
            initial_quantity=3,
            sold_quantity=0,
            cost_price=50.0,
        )
    )

    assistant_svc = CommerceAssistantService(session)

    # Buscar "auto" encuentra el producto de "vehículo" por sinónimos
    matched = assistant_svc.search_relevant_products("accesorios para auto")
    item_nums = [p.item_number for p in matched]
    assert 888 in item_nums

    # Reconocer "proyecto 12" y "proyecto #12" como item_number = 12
    assert assistant_svc.extract_item_numbers("dame información del proyecto 12") == [
        12
    ]
    assert assistant_svc.extract_item_numbers("dame información del proyecto #12") == [
        12
    ]
    assert assistant_svc.extract_item_numbers("ficha 888") == [888]

    # Cuando busca directamente el #888
    direct_match = assistant_svc.search_relevant_products(
        "información del proyecto 888"
    )
    assert len(direct_match) == 1
    assert direct_match[0].item_number == 888
