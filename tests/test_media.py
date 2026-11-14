from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.utils import get_password_hash
from app.models.user import User
from tests.conftest import get_authorization_headers


@pytest.fixture(name="auth_user")
def auth_user_fixture(session: Session) -> User:
    user = User(
        username="media_tester",
        email="media@example.com",
        password_hash=get_password_hash("Secret123*"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, auth_user: User) -> dict:
    return get_authorization_headers(client, auth_user.username, "Secret123*")


def test_media_upload_requires_auth(client: TestClient):
    """Uploading media without authentication must return 401."""
    files = {"file": ("test.png", b"fake image bytes", "image/png")}
    res = client.post("/api/core/media/upload", files=files)
    assert res.status_code == 401


def test_media_upload_rejects_invalid_mime_type(client: TestClient, auth_headers: dict):
    """Uploading non-image files (e.g. PDF or plain text) must return 400."""
    files = {"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")}
    res = client.post("/api/core/media/upload", files=files, headers=auth_headers)
    assert res.status_code == 400
    assert "no permitido" in res.json()["detail"].lower()


def test_media_upload_success_mocked(client: TestClient, auth_headers: dict):
    """Uploading a valid image calls Cloudinary and returns formatted payload."""
    mock_upload_response = {
        "secure_url": "https://res.cloudinary.com/novalabs-bo/image/upload/v12345/uyuni/avatars/sample.webp",
        "public_id": "uyuni/avatars/sample",
        "format": "webp",
        "bytes": 45000,
        "width": 500,
        "height": 500,
    }

    with (
        patch(
            "app.core.storage.cloudinary_service.cloudinary_service.is_configured",
            return_value=True,
        ),
        patch("cloudinary.uploader.upload", return_value=mock_upload_response),
    ):
        files = {"file": ("avatar.png", b"\x89PNG\r\n\x1a\nfakebytes", "image/png")}
        res = client.post(
            "/api/core/media/upload?folder=avatars",
            files=files,
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert (
            data["url"]
            == "https://res.cloudinary.com/novalabs-bo/image/upload/v12345/uyuni/avatars/sample.webp"
        )
        assert data["public_id"] == "uyuni/avatars/sample"
        assert data["format"] == "webp"
        assert data["width"] == 500
        assert data["height"] == 500


def test_media_upload_fails_when_not_configured(client: TestClient, auth_headers: dict):
    """When Cloudinary credentials are missing, API returns a clear 400 error."""
    with patch(
        "app.core.storage.cloudinary_service.cloudinary_service.is_configured",
        return_value=False,
    ):
        files = {"file": ("avatar.png", b"\x89PNG\r\n\x1a\nfakebytes", "image/png")}
        res = client.post(
            "/api/core/media/upload?folder=avatars",
            files=files,
            headers=auth_headers,
        )
        assert res.status_code == 400
        assert "no está configurado" in res.json()["detail"].lower()


def test_extract_public_id_from_url():
    """Verify regex correctly parses public_ids from Cloudinary URLs."""
    from app.core.storage.cloudinary_service import cloudinary_service

    url1 = "https://res.cloudinary.com/novalabs-bo/image/upload/v1794440964/uyuni/avatars/file_xyrq22.png"
    assert (
        cloudinary_service.extract_public_id_from_url(url1)
        == "uyuni/avatars/file_xyrq22"
    )

    url2 = "https://res.cloudinary.com/novalabs-bo/image/upload/uyuni/products/sku_100.webp"
    assert (
        cloudinary_service.extract_public_id_from_url(url2) == "uyuni/products/sku_100"
    )

    url3 = "https://images.unsplash.com/photo-1534528741775-53994a69daeb"
    assert cloudinary_service.extract_public_id_from_url(url3) is None
    assert cloudinary_service.extract_public_id_from_url(None) is None


def test_delete_image_by_url():
    """Verify delete_image_by_url calls destroy with extracted public_id."""
    from app.core.storage.cloudinary_service import cloudinary_service

    url = "https://res.cloudinary.com/novalabs-bo/image/upload/v123/uyuni/avatars/old_pic.png"

    with (
        patch.object(cloudinary_service, "is_configured", return_value=True),
        patch(
            "cloudinary.uploader.destroy", return_value={"result": "ok"}
        ) as mock_destroy,
    ):
        success = cloudinary_service.delete_image_by_url(url)
        assert success is True
        mock_destroy.assert_called_once_with("uyuni/avatars/old_pic")


def test_profile_update_deletes_old_avatar_on_replacement(
    client: TestClient, auth_user: User, auth_headers: dict, session: Session
):
    """
    When a user updates their avatar_url, the previous Cloudinary avatar is deleted.
    """
    from app.core.storage.cloudinary_service import cloudinary_service

    auth_user.avatar_url = "https://res.cloudinary.com/novalabs-bo/image/upload/v1/uyuni/avatars/old_avatar.png"
    session.add(auth_user)
    session.commit()
    session.refresh(auth_user)

    new_avatar = "https://res.cloudinary.com/novalabs-bo/image/upload/v2/uyuni/avatars/new_avatar.png"

    with patch.object(
        cloudinary_service, "delete_image_by_url", return_value=True
    ) as mock_delete:
        res = client.patch(
            "/api/auth/me",
            json={"avatar_url": new_avatar},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["avatar_url"] == new_avatar
        mock_delete.assert_called_once_with(
            "https://res.cloudinary.com/novalabs-bo/image/upload/v1/uyuni/avatars/old_avatar.png"
        )


def test_delete_avatar_me_endpoint(
    client: TestClient, auth_user: User, auth_headers: dict, session: Session
):
    """
    DELETE /api/auth/me/avatar removes image from Cloudinary and clears avatar_url.
    """
    from app.core.storage.cloudinary_service import cloudinary_service

    auth_user.avatar_url = "https://res.cloudinary.com/novalabs-bo/image/upload/v99/uyuni/avatars/to_delete.png"
    session.add(auth_user)
    session.commit()
    session.refresh(auth_user)

    with patch.object(
        cloudinary_service, "delete_image_by_url", return_value=True
    ) as mock_delete:
        res = client.delete("/api/auth/me/avatar", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["avatar_url"] is None
        mock_delete.assert_called_once_with(
            "https://res.cloudinary.com/novalabs-bo/image/upload/v99/uyuni/avatars/to_delete.png"
        )

    # Verify persisted in database
    get_res = client.get("/api/auth/me", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["avatar_url"] is None


def test_patch_avatar_null_or_empty_cleans_cloudinary(
    client: TestClient, auth_user: User, auth_headers: dict, session: Session
):
    """PATCH /api/auth/me with avatar_url=null or empty cleans previous image."""
    from app.core.storage.cloudinary_service import cloudinary_service

    auth_user.avatar_url = "https://res.cloudinary.com/novalabs-bo/image/upload/v10/uyuni/avatars/avatar_10.png"
    session.add(auth_user)
    session.commit()
    session.refresh(auth_user)

    with patch.object(
        cloudinary_service, "delete_image_by_url", return_value=True
    ) as mock_delete:
        res = client.patch(
            "/api/auth/me",
            json={"avatar_url": None},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["avatar_url"] is None
        mock_delete.assert_called_once_with(
            "https://res.cloudinary.com/novalabs-bo/image/upload/v10/uyuni/avatars/avatar_10.png"
        )
