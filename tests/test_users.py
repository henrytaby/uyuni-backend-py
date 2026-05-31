from fastapi.testclient import TestClient


def test_users_crud_as_superuser(client: TestClient, superuser_token_headers: dict):
    # 1. Create a user
    create_payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": "strongpassword123",
        "is_active": True,
        "is_superuser": False,
        "is_verified": True,
    }
    response = client.post(
        "/api/core/users/", json=create_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    created_data = response.json()
    assert created_data["username"] == "newuser"
    assert created_data["email"] == "newuser@example.com"
    assert "id" in created_data
    user_id = created_data["id"]

    # 2. List users (should include superuser and newuser)
    response = client.get("/api/core/users/", headers=superuser_token_headers)
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) >= 2
    assert any(u["username"] == "newuser" for u in users_list)

    # 3. Get user count
    response = client.get("/api/core/users/count", headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 2

    # 4. Get individual user
    response = client.get(
        f"/api/core/users/{user_id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    detail_data = response.json()
    assert detail_data["username"] == "newuser"

    # 5. Update user
    update_payload = {
        "first_name": "UpdatedName",
        "password": "newpassword456",
    }
    response = client.patch(
        f"/api/core/users/{user_id}",
        json=update_payload,
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["first_name"] == "UpdatedName"

    # 6. Delete user
    response = client.delete(
        f"/api/core/users/{user_id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify user is deleted
    response = client.get(
        f"/api/core/users/{user_id}", headers=superuser_token_headers
    )
    assert response.status_code == 404


def test_create_user_duplicate_username_or_email(
    client: TestClient, superuser_token_headers: dict
):
    # Create first user
    user1_payload = {
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123",
    }
    response = client.post(
        "/api/core/users/", json=user1_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200

    # Try duplicate username
    dup_user_payload = {
        "username": "user1",
        "email": "diff@example.com",
        "password": "password123",
    }
    response = client.post(
        "/api/core/users/", json=dup_user_payload, headers=superuser_token_headers
    )
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

    # Try duplicate email
    dup_email_payload = {
        "username": "diffuser",
        "email": "user1@example.com",
        "password": "password123",
    }
    response = client.post(
        "/api/core/users/", json=dup_email_payload, headers=superuser_token_headers
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_users_crud_requires_authentication(client: TestClient):
    response = client.get("/api/core/users/")
    assert response.status_code == 401
