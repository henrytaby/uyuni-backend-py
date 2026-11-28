from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import utils
from app.auth.utils import get_password_hash
from app.models.user import User, UserLogLogin, UserRevokedToken


@pytest.fixture(name="auth_user")
def auth_user_fixture(session: Session) -> User:
    user = User(
        username="auth_test_user",
        email="auth_test@example.com",
        first_name="Auth",
        last_name="Tester",
        password_hash=get_password_hash("SecretPass123*"),
        is_superuser=False,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="second_user")
def second_user_fixture(session: Session) -> User:
    user = User(
        username="second_test_user",
        email="second_test@example.com",
        first_name="Second",
        last_name="Tester",
        password_hash=get_password_hash("SecretPass123*"),
        is_superuser=False,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login_user(
    client: TestClient, username: str, password: str = "SecretPass123*"
) -> dict:
    res = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    assert res.status_code == 200
    return res.json()


# =====================================================================
# Tests for POST /api/auth/refresh
# =====================================================================


def test_refresh_token_via_json_body(
    client: TestClient, auth_user: User, session: Session
):
    """Frontend use case: refresh session sending refresh_token in JSON Body."""
    tokens = login_user(client, auth_user.username)
    refresh_token = tokens["refresh_token"]

    import time

    time.sleep(1.05)

    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    data = res.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] != tokens["access_token"]
    assert data["refresh_token"] != refresh_token

    # Verify old refresh token is marked as revoked (Token Rotation)
    revoked = session.exec(
        select(UserRevokedToken).where(UserRevokedToken.token == refresh_token)
    ).first()
    assert revoked is not None
    assert revoked.user_id == auth_user.id

    # The newly issued access token must work on protected endpoints
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == auth_user.username


def test_refresh_token_rotation_prevents_replay(client: TestClient, auth_user: User):
    """Replaying an old refresh token must be rejected with 401."""
    tokens = login_user(client, auth_user.username)
    old_refresh_token = tokens["refresh_token"]

    # First rotation succeeds
    res1 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh_token})
    assert res1.status_code == 200

    # Attempting to reuse old_refresh_token must fail with 401
    res2 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh_token})
    assert res2.status_code == 401
    assert "revoked" in res2.json()["detail"].lower()


def test_refresh_token_backwards_compatibility_query_param(
    client: TestClient, auth_user: User
):
    """Legacy clients sending ?refresh_token=... must continue working."""
    tokens = login_user(client, auth_user.username)
    refresh_token = tokens["refresh_token"]

    res = client.post(f"/api/auth/refresh?refresh_token={refresh_token}")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_missing_payload_returns_400(client: TestClient):
    """Calling /refresh without any token returns 400 Bad Request."""
    res_empty = client.post("/api/auth/refresh")
    assert res_empty.status_code == 400
    assert "refresh token is required" in res_empty.json()["detail"].lower()

    res_empty_json = client.post("/api/auth/refresh", json={})
    assert res_empty_json.status_code == 400
    assert "refresh token is required" in res_empty_json.json()["detail"].lower()


def test_refresh_token_invalid_or_forged_returns_401(client: TestClient):
    """Malformed or forged refresh token returns 401 Unauthorized."""
    res = client.post("/api/auth/refresh", json={"refresh_token": "not.a.valid.jwt"})
    assert res.status_code == 401


def test_refresh_token_deactivated_user_returns_401(
    client: TestClient, auth_user: User, session: Session
):
    """Refresh token for a deactivated user must return 401."""
    tokens = login_user(client, auth_user.username)
    refresh_token = tokens["refresh_token"]

    # Deactivate user
    auth_user.is_active = False
    session.add(auth_user)
    session.commit()

    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401


# =====================================================================
# Tests for POST /api/auth/logout
# =====================================================================


def test_logout_with_expired_access_token_and_refresh_token(
    client: TestClient, auth_user: User, session: Session
):
    """
    CRITICAL FRONTEND OBSERVATION:
    When access_token is already expired (e.g., after 30 min) and user logs out,
    /api/auth/logout must NOT return 401. It must revoke both tokens successfully.
    """
    # Create an expired access token
    expired_access_token = utils.create_access_token(
        data={"sub": auth_user.username, "id": auth_user.id, "email": auth_user.email},
        expires_delta=timedelta(minutes=-10),
    )

    # Create a valid refresh token
    valid_refresh_token = utils.create_access_token(
        data={"sub": auth_user.username, "id": auth_user.id, "email": auth_user.email},
        expires_delta=timedelta(days=7),
    )

    # Create dummy login log to verify logged_out_at update
    login_log = UserLogLogin(
        user_id=auth_user.id,
        username=auth_user.username,
        token=expired_access_token,
        ip_address="127.0.0.1",
        host_info="test-client",
        is_successful=True,
    )
    session.add(login_log)
    session.commit()

    # Call /logout with expired access token in Header and refresh token in Body
    res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {expired_access_token}"},
        json={"refresh_token": valid_refresh_token},
    )

    assert res.status_code == 200
    assert res.json() == {"msg": "Successfully logged out"}

    # Verify both tokens are revoked
    revoked_access = session.exec(
        select(UserRevokedToken).where(UserRevokedToken.token == expired_access_token)
    ).first()
    assert revoked_access is not None

    revoked_refresh = session.exec(
        select(UserRevokedToken).where(UserRevokedToken.token == valid_refresh_token)
    ).first()
    assert revoked_refresh is not None

    # Verify login log was updated
    session.refresh(login_log)
    assert login_log.logged_out_at is not None


def test_logout_with_only_refresh_token_in_body(
    client: TestClient, auth_user: User, session: Session
):
    """
    When client has no Authorization header (or already discarded expired token),
    calling /logout with only refresh_token in Body must succeed with 200.
    """
    valid_refresh_token = utils.create_access_token(
        data={"sub": auth_user.username, "id": auth_user.id, "email": auth_user.email},
        expires_delta=timedelta(days=7),
    )

    res = client.post(
        "/api/auth/logout",
        json={"refresh_token": valid_refresh_token},
    )

    assert res.status_code == 200
    assert res.json() == {"msg": "Successfully logged out"}

    # Verify refresh token is revoked
    revoked_refresh = session.exec(
        select(UserRevokedToken).where(UserRevokedToken.token == valid_refresh_token)
    ).first()
    assert revoked_refresh is not None
    assert revoked_refresh.user_id == auth_user.id


def test_logout_with_only_expired_access_token_in_header(
    client: TestClient, auth_user: User, session: Session
):
    """
    When user logs out with only an expired access token in Authorization header,
    it must still revoke the access token and succeed with 200.
    """
    expired_access_token = utils.create_access_token(
        data={"sub": auth_user.username, "id": auth_user.id, "email": auth_user.email},
        expires_delta=timedelta(minutes=-5),
    )

    res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )

    assert res.status_code == 200
    assert res.json() == {"msg": "Successfully logged out"}

    revoked = session.exec(
        select(UserRevokedToken).where(UserRevokedToken.token == expired_access_token)
    ).first()
    assert revoked is not None


def test_logout_standard_active_session(
    client: TestClient, auth_user: User, session: Session
):
    """Standard happy path: active access token + refresh token."""
    tokens = login_user(client, auth_user.username)
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert res.status_code == 200

    # Once logged out, access token can no longer be used for protected routes
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 401

    # And refresh token cannot be used to refresh
    refresh_res = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401


def test_logout_token_ownership_mismatch_returns_401(
    client: TestClient, auth_user: User, second_user: User
):
    """
    Security check: an access token belonging to User A cannot revoke
    a refresh token belonging to User B.
    """
    tokens_a = login_user(client, auth_user.username)
    tokens_b = login_user(client, second_user.username)

    res = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
        json={"refresh_token": tokens_b["refresh_token"]},
    )
    assert res.status_code == 401
    assert "ownership" in res.json()["detail"].lower()


def test_logout_without_any_token_returns_401(client: TestClient):
    """Calling /logout without header and without body returns 401."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 401


def test_logout_with_forged_tokens_returns_401(client: TestClient):
    """Calling /logout with forged access or refresh token returns 401."""
    res1 = client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer forged.token.here"},
    )
    assert res1.status_code == 401

    res2 = client.post(
        "/api/auth/logout",
        json={"refresh_token": "forged.token.here"},
    )
    assert res2.status_code == 401
