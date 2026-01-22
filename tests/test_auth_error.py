from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.user import UserLogLogin


def test_login_user_not_found(client: TestClient, session: Session):
    """
    Regression Test: Ensure that logging in with a non-existent user
    returns 401 Unauthorized AND logs the attempt.
    """
    username_attempt = "this_user_does_not_exist_at_all"
    login_data = {
        "username": username_attempt,
        "password": "some_password",
    }
    # Note: /api/auth/login expects form-data
    response = client.post("/api/auth/login", data=login_data)

    assert response.status_code == 401

    # Check UserLogLogin
    log = session.exec(
        select(UserLogLogin).where(UserLogLogin.username == username_attempt)
    ).first()
    assert log is not None
    assert log.is_successful is False
    assert log.user_id is None


def test_login_wrong_password(client: TestClient, session: Session, superuser):
    """
    Test: Ensure that logging in with an EXISTING user but wrong password
    logs the attempt in UserLogLogin.
    """
    # superuser fixture creates a user with password "password"
    login_data = {
        "username": superuser.username,
        "password": "wrong_password",
    }

    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 401

    # Check UserLogLogin
    log = session.exec(
        select(UserLogLogin)
        .where(UserLogLogin.username == superuser.username)
        .where(UserLogLogin.is_successful == False)  # noqa: E712
    ).first()

    assert log is not None
    assert log.user_id == superuser.id
