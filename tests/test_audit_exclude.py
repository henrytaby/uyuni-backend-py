from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models.audit import AuditLog


def test_audit_exclude_404(
    client: TestClient, session: Session, superuser_token_headers
):
    # 1. Ensure 404 is in exclusion list (default)
    assert 404 in settings.AUDIT_LOG_EXCLUDE_STATUS_CODES

    # 2. Get initial count of audit logs
    initial_count = session.exec(select(AuditLog)).all()

    # 3. Perform a request to a non-existent endpoint
    response = client.get(
        "/api/v1/non-existent-endpoint", headers=superuser_token_headers
    )
    assert response.status_code == 404

    # 4. Check Audit Log (Should NOT increase)
    session.expire_all()
    final_count = session.exec(select(AuditLog)).all()

    # We expect the count to be the same, meaning no log was added
    assert len(final_count) == len(initial_count)


def test_audit_exclude_method(
    client: TestClient, session: Session, superuser_token_headers
):
    # 1. Override settings to exclude GET
    settings.AUDIT_LOG_INCLUDED_METHODS = ["POST", "PUT", "DELETE"]

    # 2. Get initial count
    initial_count = session.exec(select(AuditLog)).all()

    # 3. Perform a GET request (Should be ignored)
    response = client.get("/api/auth/me", headers=superuser_token_headers)
    assert response.status_code == 200

    # 4. Check Audit Log (Should NOT increase)
    session.expire_all()
    final_count = session.exec(select(AuditLog)).all()

    # Restore settings
    settings.AUDIT_LOG_INCLUDED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

    assert len(final_count) == len(initial_count)


def test_audit_exclude_catalog_path(
    client: TestClient, session: Session, superuser_token_headers
):
    # Enable access audit explicitly
    settings.ENABLE_ACCESS_AUDIT = True
    session.expire_all()
    initial_count = len(session.exec(select(AuditLog)).all())

    # Request to excluded catalog path
    _ = client.get("/api/catalogs/status", headers=superuser_token_headers)

    session.expire_all()
    final_count = len(session.exec(select(AuditLog)).all())

    # Even with ENABLE_ACCESS_AUDIT=True, /api/catalogs is in AUDIT_EXCLUDED_PATHS
    assert final_count == initial_count


def test_audit_exclude_system_entities_and_noop_updates(
    client: TestClient, session: Session, superuser_token_headers
):
    from app.models.module import Module
    from app.modules.tasks.models import Task

    settings.ENABLE_DATA_AUDIT = True

    # 1. System entity (Module) creation should not create an AuditLog
    mod = Module(
        name="Test Audit Module",
        slug="test-audit-module",
        icon="pi pi-box",
        route="/test-audit",
    )
    session.add(mod)
    session.commit()

    session.expire_all()
    module_log = session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "Module",
            AuditLog.entity_id == str(mod.id),
        )
    ).first()
    assert module_log is None

    # 2. No-op update on Task should NOT create an audit log with changes=None
    task = Task(title="Noop Test", description="Testing noop")
    session.add(task)
    session.commit()
    session.refresh(task)

    session.expire_all()
    task_logs_query = select(AuditLog).where(AuditLog.entity_id == str(task.id))
    logs_before = len(session.exec(task_logs_query).all())

    # Mark as dirty without changing any column value
    task.title = "Noop Test"
    session.add(task)
    session.commit()

    session.expire_all()
    logs_after = len(session.exec(task_logs_query).all())
    # Count should not increase because there were no actual attribute changes
    assert logs_after == logs_before

