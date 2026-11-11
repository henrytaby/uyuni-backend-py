import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.utils import get_password_hash
from app.models.user import User
from tests.conftest import get_authorization_headers


@pytest.fixture(name="normal_user")
def normal_user_fixture(session: Session) -> User:
    user = User(
        username="musharof_profile",
        email="musharof@example.com",
        first_name="Musharof",
        last_name="Chowdhury",
        phone="+59170012345",
        avatar_url="https://avatar.example.com/musharof.png",
        country="BO",
        city="Santa Cruz",
        address="Av. San Martín #450",
        timezone="America/La_Paz",
        password_hash=get_password_hash("InitialPass123*"),
        is_superuser=False,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="normal_user_headers")
def normal_user_headers_fixture(client: TestClient, normal_user: User) -> dict:
    return get_authorization_headers(client, normal_user.username, "InitialPass123*")


def test_get_me_profile_returns_full_data(
    client: TestClient, normal_user: User, normal_user_headers: dict
):
    """GET /api/auth/me should return all profile fields for the authenticated user."""
    res = client.get("/api/auth/me", headers=normal_user_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(normal_user.id)
    assert data["username"] == "musharof_profile"
    assert data["email"] == "musharof@example.com"
    assert data["first_name"] == "Musharof"
    assert data["last_name"] == "Chowdhury"
    assert data["phone"] == "+59170012345"
    assert data["avatar_url"] == "https://avatar.example.com/musharof.png"
    assert data["country"] == "BO"
    assert data["city"] == "Santa Cruz"
    assert data["address"] == "Av. San Martín #450"
    assert data["timezone"] == "America/La_Paz"
    assert data["is_active"] is True


def test_update_me_profile_success(
    client: TestClient, normal_user: User, normal_user_headers: dict
):
    """PATCH /api/auth/me allows updating own personal and contact fields."""
    update_payload = {
        "first_name": "Musharof Updated",
        "last_name": "Chowdhury Dev",
        "phone": "+59179998877",
        "avatar_url": "https://avatar.example.com/new_pic.jpg",
        "country": "BO",
        "city": "Cochabamba",
        "address": "Av. Heroínas #200",
        "timezone": "America/La_Paz",
    }
    res = client.patch("/api/auth/me", json=update_payload, headers=normal_user_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["first_name"] == "Musharof Updated"
    assert data["last_name"] == "Chowdhury Dev"
    assert data["phone"] == "+59179998877"
    assert data["avatar_url"] == "https://avatar.example.com/new_pic.jpg"
    assert data["city"] == "Cochabamba"
    assert data["address"] == "Av. Heroínas #200"

    # Verify persisted in GET /api/auth/me
    get_res = client.get("/api/auth/me", headers=normal_user_headers)
    assert get_res.status_code == 200
    assert get_res.json()["city"] == "Cochabamba"


def test_update_me_profile_rejects_forbidden_fields(
    client: TestClient, normal_user: User, normal_user_headers: dict
):
    """
    PATCH /api/auth/me rejects attempts to inject administrative or sensitive fields.
    """
    # Attempting to escalate privilege to superuser
    res = client.patch(
        "/api/auth/me",
        json={"is_superuser": True},
        headers=normal_user_headers,
    )
    assert res.status_code == 422

    # Attempting to inject roles
    res_role = client.patch(
        "/api/auth/me",
        json={"role_slugs": ["admin"]},
        headers=normal_user_headers,
    )
    assert res_role.status_code == 422

    # Attempting to change email directly via me
    res_email = client.patch(
        "/api/auth/me",
        json={"email": "hacked@example.com"},
        headers=normal_user_headers,
    )
    assert res_email.status_code == 422


def test_change_password_me_success_and_login_with_new_password(
    client: TestClient, normal_user: User, normal_user_headers: dict
):
    """
    POST /api/auth/me/change-password changes password when current password is valid.
    """
    change_payload = {
        "current_password": "InitialPass123*",
        "new_password": "BrandNewSecret2026*",
    }
    res = client.post(
        "/api/auth/me/change-password",
        json=change_payload,
        headers=normal_user_headers,
    )
    assert res.status_code == 200
    assert "exitosa" in res.json()["message"].lower()

    # Old password must fail
    old_login = client.post(
        "/api/auth/login",
        data={
            "username": normal_user.username,
            "password": "InitialPass123*",
        },
    )
    assert old_login.status_code == 401

    # New password must succeed
    new_login = client.post(
        "/api/auth/login",
        data={
            "username": normal_user.username,
            "password": "BrandNewSecret2026*",
        },
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_change_password_me_wrong_current_password(
    client: TestClient, normal_user_headers: dict
):
    """POST /api/auth/me/change-password fails with 400 if current password is wrong."""
    change_payload = {
        "current_password": "WrongPassword!",
        "new_password": "BrandNewSecret2026*",
    }
    res = client.post(
        "/api/auth/me/change-password",
        json=change_payload,
        headers=normal_user_headers,
    )
    assert res.status_code == 400
    assert "incorrecta" in res.json()["detail"].lower()


def test_change_password_me_same_password(
    client: TestClient, normal_user_headers: dict
):
    """POST /api/auth/me/change-password fails if new password is same as current."""
    change_payload = {
        "current_password": "InitialPass123*",
        "new_password": "InitialPass123*",
    }
    res = client.post(
        "/api/auth/me/change-password",
        json=change_payload,
        headers=normal_user_headers,
    )
    assert res.status_code == 400
    assert "idéntica" in res.json()["detail"].lower()


def test_change_password_me_too_short(client: TestClient, normal_user_headers: dict):
    """POST /api/auth/me/change-password fails with 422 if new password is < 6 chars."""
    change_payload = {
        "current_password": "InitialPass123*",
        "new_password": "123",
    }
    res = client.post(
        "/api/auth/me/change-password",
        json=change_payload,
        headers=normal_user_headers,
    )
    assert res.status_code == 422


def test_me_endpoints_require_authentication(client: TestClient):
    """Accessing /api/auth/me without token returns 401."""
    res_get = client.get("/api/auth/me")
    assert res_get.status_code == 401

    res_patch = client.patch("/api/auth/me", json={"first_name": "Test"})
    assert res_patch.status_code == 401

    res_pwd = client.post(
        "/api/auth/me/change-password",
        json={"current_password": "a", "new_password": "b"},
    )
    assert res_pwd.status_code == 401
