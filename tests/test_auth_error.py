
from fastapi.testclient import TestClient

def test_login_user_not_found(client: TestClient):
    """
    Regression Test: Ensure that logging in with a non-existent user
    returns 401 Unauthorized, NOT 500 Internal Server Error.
    (This verifies the fix for UnknownHashError in 'fake_hash')
    """
    login_data = {
        "username": "this_user_does_not_exist_at_all",
        "password": "some_password",
    }
    # Note: /api/auth/login expects form-data
    response = client.post("/api/auth/login", data=login_data)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
