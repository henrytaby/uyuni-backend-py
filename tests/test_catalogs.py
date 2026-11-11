import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.commerce.categories.models import Category


@pytest.fixture(name="catalog_data")
def catalog_data_fixture(session: Session):
    cat1 = Category(
        id=uuid.uuid4(),
        code="CAT-01",
        name="Electrónica",
        description="Dispositivos y gadgets",
        icon="pi pi-bolt",
        is_active=True,
    )
    cat2 = Category(
        id=uuid.uuid4(),
        code="CAT-02",
        name="Herramientas",
        description="Herramientas eléctricas y manuales",
        icon="pi pi-wrench",
        is_active=True,
    )

    session.add(cat1)
    session.add(cat2)
    session.commit()

    return {
        "cat1": cat1,
        "cat2": cat2,
    }


def test_get_static_catalog_success(client: TestClient, superuser_token_headers: dict):
    response = client.get(
        "/api/catalogs/commerce_physical_conditions", headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    values = [item["value"] for item in data]
    assert "OPERATIONAL" in values
    assert "DAMAGED_SCRAP" in values


def test_get_dynamic_categories_catalog_success(
    client: TestClient, superuser_token_headers: dict, catalog_data: dict
):
    response = client.get(
        "/api/catalogs/commerce_categories", headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    labels = [item["label"] for item in data]
    assert any("Electrónica" in label for label in labels)
    assert any("Herramientas" in label for label in labels)


def test_get_catalog_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/api/catalogs/no_existe", headers=superuser_token_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog 'no_existe' not found"


def test_get_catalog_unauthorized(client: TestClient):
    response = client.get("/api/catalogs/commerce_physical_conditions")
    assert response.status_code == 401


# --- Pruebas del Endpoint Global Bulk (POST /api/catalogs/bulk) ---


def test_post_bulk_catalogs_success(
    client: TestClient, superuser_token_headers: dict, catalog_data: dict
):
    payload = {
        "commerce_physical_conditions": {},
        "commerce_payment_methods": {},
        "commerce_categories": {},
    }
    response = client.post(
        "/api/catalogs/bulk", json=payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()

    assert "commerce_physical_conditions" in data
    assert len(data["commerce_physical_conditions"]) == 5

    assert "commerce_payment_methods" in data
    assert len(data["commerce_payment_methods"]) == 4

    assert "commerce_categories" in data
    assert len(data["commerce_categories"]) >= 2


def test_post_bulk_catalogs_not_found(
    client: TestClient, superuser_token_headers: dict
):
    payload = {"commerce_physical_conditions": {}, "no_existe": {}}
    response = client.post(
        "/api/catalogs/bulk", json=payload, headers=superuser_token_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog 'no_existe' not found"


def test_post_bulk_catalogs_unauthorized(client: TestClient):
    payload = {"commerce_physical_conditions": {}}
    response = client.post("/api/catalogs/bulk", json=payload)
    assert response.status_code == 401
