import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.core.org_units.models import OrgUnit


@pytest.fixture(name="catalog_data")
def catalog_data_fixture(session: Session):
    # 1. Crear Gerencias (parent_id is None)
    gerencia1 = OrgUnit(
        id=uuid.uuid4(),
        external_id=101,
        name="Gerencia de TI",
        type="MANAGEMENT",
        is_active=True,
    )
    gerencia2 = OrgUnit(
        id=uuid.uuid4(),
        external_id=102,
        name="Gerencia de RRHH",
        type="MANAGEMENT",
        is_active=True,
    )
    gerencia_inactive = OrgUnit(
        id=uuid.uuid4(),
        external_id=103,
        name="Gerencia Obsoleta",
        type="MANAGEMENT",
        is_active=False,
    )

    # 2. Crear Departamentos (parent_id points to Gerencia)
    dept1 = OrgUnit(
        id=uuid.uuid4(),
        external_id=201,
        name="Departamento de Desarrollo",
        type="DEPARTMENT",
        parent_id=gerencia1.id,
        is_active=True,
    )
    dept2 = OrgUnit(
        id=uuid.uuid4(),
        external_id=202,
        name="Departamento de Sistemas",
        type="DEPARTMENT",
        parent_id=gerencia1.id,
        is_active=True,
    )
    dept_inactive = OrgUnit(
        id=uuid.uuid4(),
        external_id=203,
        name="Departamento Inactivo",
        type="DEPARTMENT",
        parent_id=gerencia1.id,
        is_active=False,
    )

    session.add(gerencia1)
    session.add(gerencia2)
    session.add(gerencia_inactive)
    session.add(dept1)
    session.add(dept2)
    session.add(dept_inactive)
    session.commit()

    return {
        "gerencia1": gerencia1,
        "gerencia2": gerencia2,
        "dept1": dept1,
        "dept2": dept2,
    }


def test_get_gerencias_success(
    client: TestClient, superuser_token_headers: dict, catalog_data: dict
):
    response = client.get("/api/catalogs/gerencias", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()

    # Deben ser únicamente las gerencias activas y ordenadas alfabéticamente
    assert len(data) == 2
    assert data[0]["label"] == "Gerencia de RRHH"
    assert data[0]["value"] == str(catalog_data["gerencia2"].id)
    assert data[1]["label"] == "Gerencia de TI"
    assert data[1]["value"] == str(catalog_data["gerencia1"].id)


def test_get_departamentos_success(
    client: TestClient, superuser_token_headers: dict, catalog_data: dict
):
    gerencia_id = str(catalog_data["gerencia1"].id)
    response = client.get(
        f"/api/catalogs/departamentos?gerencia_id={gerencia_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Deben ser los departamentos activos dependientes de la gerencia1
    assert len(data) == 2
    assert data[0]["label"] == "Departamento de Desarrollo"
    assert data[0]["value"] == str(catalog_data["dept1"].id)
    assert data[1]["label"] == "Departamento de Sistemas"
    assert data[1]["value"] == str(catalog_data["dept2"].id)


def test_get_departamentos_empty_or_invalid_id(
    client: TestClient, superuser_token_headers: dict
):
    # Sin gerencia_id query param
    response = client.get(
        "/api/catalogs/departamentos", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == []

    # Con gerencia_id inválido (no es UUID)
    response = client.get(
        "/api/catalogs/departamentos?gerencia_id=invalido-uuid",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_catalog_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/api/catalogs/no_existe", headers=superuser_token_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog 'no_existe' not found"


def test_get_catalog_unauthorized(client: TestClient):
    response = client.get("/api/catalogs/gerencias")
    assert response.status_code == 401


# --- Pruebas del Endpoint Global Bulk (POST /api/catalogs/bulk) ---


def test_post_bulk_catalogs_success(
    client: TestClient, superuser_token_headers: dict, catalog_data: dict
):
    payload = {
        "gerencias": {},
        "departamentos": {"gerencia_id": str(catalog_data["gerencia1"].id)},
    }
    response = client.post(
        "/api/catalogs/bulk", json=payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()

    # Verificación de Gerencias
    assert "gerencias" in data
    assert len(data["gerencias"]) == 2
    assert data["gerencias"][0]["label"] == "Gerencia de RRHH"
    assert data["gerencias"][1]["label"] == "Gerencia de TI"

    # Verificación de Departamentos
    assert "departamentos" in data
    assert len(data["departamentos"]) == 2
    assert data["departamentos"][0]["label"] == "Departamento de Desarrollo"
    assert data["departamentos"][1]["label"] == "Departamento de Sistemas"


def test_post_bulk_catalogs_not_found(
    client: TestClient, superuser_token_headers: dict
):
    payload = {"gerencias": {}, "no_existe": {}}
    response = client.post(
        "/api/catalogs/bulk", json=payload, headers=superuser_token_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog 'no_existe' not found"


def test_post_bulk_catalogs_unauthorized(client: TestClient):
    payload = {"gerencias": {}}
    response = client.post("/api/catalogs/bulk", json=payload)
    assert response.status_code == 401
