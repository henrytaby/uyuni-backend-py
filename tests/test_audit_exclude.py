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
