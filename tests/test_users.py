from fastapi.testclient import TestClient
from sqlmodel import Session


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
    response = client.get(f"/api/core/users/{user_id}", headers=superuser_token_headers)
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
    response = client.get(f"/api/core/users/{user_id}", headers=superuser_token_headers)
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


def test_user_roles_assignment_and_sync(
    client: TestClient, session: Session, superuser_token_headers: dict
):
    from app.core.manifests import global_manifest_registry

    global_manifest_registry.sync(session)

    # 1. Create user with role_slugs=["admin"]
    create_payload = {
        "username": "roleuser",
        "email": "roleuser@example.com",
        "password": "strongpassword123",
        "role_slugs": ["admin"],
    }
    response = client.post(
        "/api/core/users/", json=create_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "admin" in data["role_slugs"]
    assert any(r["slug"] == "admin" for r in data["roles"])
    user_id = data["id"]

    # 2. Get user by ID and check roles
    response = client.get(f"/api/core/users/{user_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    user_detail = response.json()
    assert user_detail["role_slugs"] == ["admin"]
    assert len(user_detail["roles"]) == 1
    assert user_detail["roles"][0]["name"] == "Administrador Sistema"

    # 3. Update roles via PATCH: remove admin by providing empty list
    patch_payload = {"role_slugs": []}
    response = client.patch(
        f"/api/core/users/{user_id}",
        json=patch_payload,
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["role_slugs"] == []
    assert response.json()["roles"] == []

    # 4. Re-assign role via dedicated endpoint POST /{id}/roles/{role_slug}
    response = client.post(
        f"/api/core/users/{user_id}/roles/admin",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert "admin" in response.json()["role_slugs"]

    # 5. Remove role via dedicated endpoint DELETE /{id}/roles/{role_slug}
    response = client.delete(
        f"/api/core/users/{user_id}/roles/admin",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["role_slugs"] == []

    # 6. Try to assign invalid role slug -> 400 Bad Request
    response = client.post(
        f"/api/core/users/{user_id}/roles/non_existent_role",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert "not found or inactive" in response.json()["detail"]


def test_roles_catalog_endpoints(
    client: TestClient, session: Session, superuser_token_headers: dict
):
    from app.core.manifests import global_manifest_registry

    global_manifest_registry.sync(session)

    # 1. Single selector: GET /api/catalogs/roles
    response = client.get("/api/catalogs/roles", headers=superuser_token_headers)
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    assert any(r["value"] == "admin" for r in roles)

    # 2. Single selector: GET /api/catalogs/core_roles
    response = client.get("/api/catalogs/core_roles", headers=superuser_token_headers)
    assert response.status_code == 200
    core_roles = response.json()
    assert any(r["value"] == "admin" for r in core_roles)

    # 3. Bulk loader: POST /api/catalogs/bulk with "roles"
    bulk_payload = {"roles": {}}
    response = client.post(
        "/api/catalogs/bulk", json=bulk_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    bulk_data = response.json()
    assert "roles" in bulk_data
    assert any(r["value"] == "admin" for r in bulk_data["roles"])


def test_user_login_history_endpoints(
    client: TestClient, superuser, superuser_token_headers: dict
):
    import uuid

    # 1. Query login history for superuser (created during token fixture login)
    response = client.get(
        f"/api/core/users/{superuser.id}/logins",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    first_log = logs[0]
    assert "ip_address" in first_log
    assert "host_info" in first_log
    assert first_log["is_successful"] is True
    # Ensure sensitive fields are not exposed
    assert "token" not in first_log

    # 2. Count logins for superuser
    response = client.get(
        f"/api/core/users/{superuser.id}/logins/count",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    # 3. Filter by is_successful=True
    response = client.get(
        f"/api/core/users/{superuser.id}/logins?is_successful=true",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # 4. Filter by is_successful=False (should be 0)
    response = client.get(
        f"/api/core/users/{superuser.id}/logins?is_successful=false",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    # 5. Non-existent user -> 404 Not Found
    random_id = uuid.uuid4()
    response = client.get(
        f"/api/core/users/{random_id}/logins",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_user_strict_validation_username_and_email(
    client: TestClient, superuser_token_headers: dict
):
    # 1. Username with spaces (e.g. "henry. taby")
    bad_payload = {
        "username": "henry. taby",
        "email": "henry@example.com",
        "password": "validpassword123",
    }
    response = client.post(
        "/api/core/users/", json=bad_payload, headers=superuser_token_headers
    )
    assert response.status_code == 422
    assert "no puede contener espacios" in str(response.json())

    # 2. Username with consecutive special characters (e.g. "henry..taby")
    bad_payload["username"] = "henry..taby"
    response = client.post(
        "/api/core/users/", json=bad_payload, headers=superuser_token_headers
    )
    assert response.status_code == 422
    assert "consecutivos" in str(response.json())

    # 3. Username starting or ending with dot/dash/underscore
    bad_payload["username"] = ".henry"
    response = client.post(
        "/api/core/users/", json=bad_payload, headers=superuser_token_headers
    )
    assert response.status_code == 422

    # 4. Invalid email format
    bad_email_payload = {
        "username": "validuser",
        "email": "not-an-email",
        "password": "validpassword123",
    }
    response = client.post(
        "/api/core/users/",
        json=bad_email_payload,
        headers=superuser_token_headers,
    )
    assert response.status_code == 422

    # 5. Short password (< 6 characters)
    short_pw_payload = {
        "username": "validuser",
        "email": "valid@example.com",
        "password": "123",
    }
    response = client.post(
        "/api/core/users/", json=short_pw_payload, headers=superuser_token_headers
    )
    assert response.status_code == 422

    # 6. Valid user normalizes username and email to lowercase
    valid_payload = {
        "username": "Henry.Taby",
        "email": "Henry.Taby@Example.Com",
        "password": "strongpassword123",
        "first_name": "  Henry  ",
    }
    response = client.post(
        "/api/core/users/", json=valid_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    created = response.json()
    assert created["username"] == "henry.taby"
    assert created["email"] == "henry.taby@example.com"
    assert created["first_name"] == "Henry"
    user_id = created["id"]

    # 7. Updating user with space in username -> 422
    update_res = client.patch(
        f"/api/core/users/{user_id}",
        json={"username": "invalid username"},
        headers=superuser_token_headers,
    )
    assert update_res.status_code == 422

    # 8. Updating user with invalid email -> 422
    update_res = client.patch(
        f"/api/core/users/{user_id}",
        json={"email": "bademail"},
        headers=superuser_token_headers,
    )
    assert update_res.status_code == 422


def test_user_profile_fields_crud_and_search(
    client: TestClient, superuser_token_headers: dict
):
    # 1. Create user with full profile fields
    profile_payload = {
        "username": "streamer_dan",
        "email": "dan@empresa.com",
        "password": "danpassword123",
        "first_name": "Daniel",
        "last_name": "Rojas",
        "phone": "+591 70123456",
        "avatar_url": "https://pub-cdn.empresa.com/avatars/dan.webp",
        "country": "BO",
        "city": "Cochabamba",
        "address": "Av. América 123",
        "notes": "Streamer titular turno noche TikTok Live",
        "timezone": "America/La_Paz",
    }
    response = client.post(
        "/api/core/users/", json=profile_payload, headers=superuser_token_headers
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "streamer_dan"
    assert user_data["phone"] == "+591 70123456"
    assert user_data["avatar_url"] == "https://pub-cdn.empresa.com/avatars/dan.webp"
    assert user_data["city"] == "Cochabamba"
    assert user_data["country"] == "BO"
    assert user_data["address"] == "Av. América 123"
    assert user_data["notes"] == "Streamer titular turno noche TikTok Live"
    assert user_data["timezone"] == "America/La_Paz"
    user_id = user_data["id"]

    # 2. Update profile fields
    patch_payload = {
        "phone": "+591 77998811",
        "city": "Santa Cruz",
        "address": "Equipetrol Calle 4",
    }
    response = client.patch(
        f"/api/core/users/{user_id}",
        json=patch_payload,
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["phone"] == "+591 77998811"
    assert updated["city"] == "Santa Cruz"
    assert updated["address"] == "Equipetrol Calle 4"
    assert updated["notes"] == "Streamer titular turno noche TikTok Live"

    # 3. Global search by phone
    response = client.get(
        "/api/core/users/?search=77998811", headers=superuser_token_headers
    )
    assert response.status_code == 200
    search_results = response.json()
    assert any(u["id"] == user_id for u in search_results)

    # 4. Global search by city
    response = client.get(
        "/api/core/users/?search=Santa Cruz", headers=superuser_token_headers
    )
    assert response.status_code == 200
    search_results = response.json()
    assert any(u["id"] == user_id for u in search_results)
