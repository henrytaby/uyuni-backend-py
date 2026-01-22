from unittest.mock import patch

from app.auth import utils
from app.core.config import settings
from app.models.user import User


def test_login_lockout_flow(client, session):
    # 1. Create a user
    password = "password123"
    hashed = utils.get_password_hash(password)
    user = User(
        username="lockout_user",
        email="lockout@example.com",
        password_hash=hashed,
        is_active=True,
    )
    session.add(user)
    session.commit()

    # 2. Configure stricter lockout for testing
    # We patch the settings to avoid waiting for defaults
    # MAX_ATTEMPTS = 3
    # LOCKOUT_MINUTES = 1 (we just need it to be > 0)

    with (
        patch.object(settings, "SECURITY_LOGIN_MAX_ATTEMPTS", 3),
        patch.object(settings, "SECURITY_LOCKOUT_MINUTES", 15),
    ):
        url = "/api/auth/login"
        bad_data = {"username": "lockout_user", "password": "wrongpassword"}

        # Attempt 1 (Failure)
        r = client.post(url, data=bad_data)
        assert r.status_code == 401

        # Attempt 2 (Failure)
        r = client.post(url, data=bad_data)
        assert r.status_code == 401

        # Attempt 3 (Failure -> Triggers Lockout)
        r = client.post(url, data=bad_data)
        assert r.status_code == 401
        # Internal logic: 3rd failed attempt sets lock.
        # The 3rd attempt itself returns 401 (Invalid Credentials),
        # but SETS the lock for FUTURE attempts.

        # Attempt 4 (Should be Locked)
        r = client.post(url, data=bad_data)
        assert r.status_code == 403
        data = r.json()

        # Verify Structure
        assert data["detail"]["code"] == "ACCOUNT_LOCKED"
        assert "unlock_at" in data["detail"]
        assert "wait_seconds" in data["detail"]
        assert "message" in data["detail"]
        assert data["detail"]["max_attempts"] == 3
        assert data["detail"]["lockout_minutes"] == 15

        # Verify Header
        assert "retry-after" in r.headers
        wait_seconds = data["detail"]["wait_seconds"]
        assert r.headers["retry-after"] == str(wait_seconds)
