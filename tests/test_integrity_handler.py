from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.handlers import integrity_error_handler


def test_integrity_error_handler_unique():
    # Setup test FastAPI app
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-unique")
    def trigger_unique():
        # Simulate SQLite/generic unique constraint failure
        raise IntegrityError(
            statement="INSERT INTO table...",
            params={},
            orig=Exception("UNIQUE constraint failed: core_staff.email"),
        )

    client = TestClient(test_app)
    response = client.get("/trigger-unique")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Ya existe un registro con el valor duplicado en: email."
    }


def test_integrity_error_handler_fk():
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-fk")
    def trigger_fk():
        # Simulate SQLite/generic foreign key constraint failure
        raise IntegrityError(
            statement="INSERT INTO table...",
            params={},
            orig=Exception("FOREIGN KEY constraint failed"),
        )

    client = TestClient(test_app)
    response = client.get("/trigger-fk")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "La relación especificada (clave foránea) no existe o no es válida."
    }


def test_integrity_error_handler_not_null():
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-not-null")
    def trigger_not_null():
        # Simulate SQLite/generic not null failure
        raise IntegrityError(
            statement="INSERT INTO table...",
            params={},
            orig=Exception("NOT NULL constraint failed: core_staff.first_name"),
        )

    client = TestClient(test_app)
    response = client.get("/trigger-not-null")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "El campo 'first_name' es requerido y no puede ser nulo."
    }


def test_integrity_error_handler_postgres_unique():
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-pg-unique")
    def trigger_pg_unique():
        # Mock psycopg2 exception with pgcode
        class MockDiag:
            message_detail = "Key (email)=(test@example.com) already exists."

        class MockOrigException(Exception):
            pgcode = "23505"
            diag = MockDiag()

        raise IntegrityError(
            statement="INSERT INTO table...", params={}, orig=MockOrigException()
        )

    client = TestClient(test_app)
    response = client.get("/trigger-pg-unique")
    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Ya existe un registro con el valor 'test@example.com' "
            "para el campo 'email'."
        )
    }


def test_integrity_error_handler_postgres_fk():
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-pg-fk")
    def trigger_pg_fk():
        class MockDiag:
            message_detail = (
                "Key (org_unit_id)=(3fa85f64-5717-4562-b3fc-2c963f66afa6) "
                'is not present in table "core_org_unit".'
            )

        class MockOrigException(Exception):
            pgcode = "23503"
            diag = MockDiag()

        raise IntegrityError(
            statement="INSERT INTO table...", params={}, orig=MockOrigException()
        )

    client = TestClient(test_app)
    response = client.get("/trigger-pg-fk")
    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "El valor '3fa85f64-5717-4562-b3fc-2c963f66afa6' especificado para el "
            "campo 'org_unit_id' no existe en la tabla de referencia 'core_org_unit'."
        )
    }


def test_integrity_error_handler_postgres_not_null():
    test_app = FastAPI()
    test_app.add_exception_handler(IntegrityError, integrity_error_handler)

    @test_app.get("/trigger-pg-not-null")
    def trigger_pg_not_null():
        class MockDiag:
            column_name = "username"

        class MockOrigException(Exception):
            pgcode = "23502"
            diag = MockDiag()

        raise IntegrityError(
            statement="INSERT INTO table...", params={}, orig=MockOrigException()
        )

    client = TestClient(test_app)
    response = client.get("/trigger-pg-not-null")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "El campo 'username' es requerido y no puede ser nulo."
    }
