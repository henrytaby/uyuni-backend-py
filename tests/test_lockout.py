import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.user import User
from app.auth.utils import get_password_hash

def test_account_lockout_flow(client: TestClient, session: Session):
    # 1. Create a test user directly in DB
    password = "securepassword"
    user = User(
        username="lockout_test",
        email="lockout@example.com",
        password_hash=get_password_hash(password),
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Fail 5 times
    for i in range(5):
        response = client.post(
            "/api/auth/login",
            data={"username": "lockout_test", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        
        # Verify counter incremented
        session.refresh(user)
        assert user.failed_login_attempts == i + 1

    # 3. Attempt 6 (Should be Locked)
    response = client.post(
        "/api/auth/login",
        data={"username": "lockout_test", "password": "wrongpassword"}
    )
    assert response.status_code == 403
    assert "Account is locked" in response.json()["detail"]

    # 4. Attempt with CORRECT password (Should still be Locked)
    response = client.post(
        "/api/auth/login",
        data={"username": "lockout_test", "password": password}
    )
    assert response.status_code == 403
    
    # 5. Manually unlock for testing reset
    user.locked_until = None
    session.add(user)
    session.commit()

    # 6. Login Success -> Should reset counter (which was 5)
    response = client.post(
        "/api/auth/login",
        data={"username": "lockout_test", "password": password}
    )
    assert response.status_code == 200
    
    session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.last_login_at is not None
