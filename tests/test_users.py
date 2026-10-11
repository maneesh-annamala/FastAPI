from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_user


## -------------------------------------------------------------
## User Registration & Validation
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_create_user_success(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data


@pytest.mark.anyio
async def test_create_user_validation_error(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={
            "username": "testuser",
        },
    )
    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text


@pytest.mark.anyio
async def test_create_user_duplicate_email(client: AsyncClient):
    await create_test_user(client)

    response = await client.post(
        "/api/users",
        json={
            "username": "different_user",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 405
    assert response.json()["detail"] == "Email already registered"


## -------------------------------------------------------------
## Token Authentication & Current User
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_login_for_access_token_success(client: AsyncClient):
    await create_test_user(
        client,
        username="tokenuser",
        email="tokenuser@example.com",
        password="secretpassword123",
    )
    response = await client.post(
        "/api/users/token",
        data={
            "username": "tokenuser@example.com",
            "password": "secretpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_for_access_token_invalid_password(client: AsyncClient):
    await create_test_user(
        client,
        username="tokenuser",
        email="tokenuser@example.com",
        password="secretpassword123",
    )
    response = await client.post(
        "/api/users/token",
        data={
            "username": "tokenuser@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.anyio
async def test_get_users_list_success(client: AsyncClient):
    await create_test_user(client, username="alice", email="alice@example.com")
    await create_test_user(client, username="bob", email="bob@example.com")
    token = await login_user(client, email="alice@example.com")

    response = await client.get("/api/users", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert "alice" in usernames
    assert "bob" in usernames


@pytest.mark.anyio
async def test_get_users_list_unauthorized(client: AsyncClient):
    response = await client.get("/api/users")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_current_user_success(client: AsyncClient):
    user = await create_test_user(
        client, username="currentme", email="currentme@example.com"
    )
    token = await login_user(client, email="currentme@example.com")

    response = await client.get("/api/users/current_user", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user["id"]
    assert data["username"] == "currentme"
    assert data["email"] == "currentme@example.com"


@pytest.mark.anyio
async def test_get_current_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/users/current_user")
    assert response.status_code == 401


## -------------------------------------------------------------
## User's Posts Listing
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_get_user_posts_success(client: AsyncClient):
    user = await create_test_user(client, username="writer", email="writer@example.com")
    token = await login_user(client, email="writer@example.com")
    headers = auth_header(token)

    for i in range(3):
        create_resp = await client.post(
            "/api/posts",
            json={"title": f"Writer Post {i}", "content": f"Content of post {i}"},
            headers=headers,
        )
        assert create_resp.status_code == 201

    response = await client.get(f"/api/users/{user['id']}/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["posts"]) == 3
    assert data["posts"][0]["author"]["username"] == "writer"


@pytest.mark.anyio
async def test_get_user_posts_not_found(client: AsyncClient):
    response = await client.get("/api/users/999999/posts")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


## -------------------------------------------------------------
## User Profile Update
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_update_user_profile_success(client: AsyncClient):
    user = await create_test_user(
        client, username="oldname", email="oldemail@example.com"
    )
    token = await login_user(client, email="oldemail@example.com")

    response = await client.patch(
        f"/api/users/{user['id']}",
        json={"username": "newname", "email": "newemail@example.com"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newname"
    assert data["email"] == "newemail@example.com"


@pytest.mark.anyio
async def test_update_user_profile_unauthorized_user(client: AsyncClient):
    user1 = await create_test_user(client, username="u1", email="u1@example.com")
    await create_test_user(client, username="u2", email="u2@example.com")
    token2 = await login_user(client, email="u2@example.com")

    response = await client.patch(
        f"/api/users/{user1['id']}",
        json={"username": "hackedname"},
        headers=auth_header(token2),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Un-Authorized Action"


@pytest.mark.anyio
async def test_update_user_profile_duplicate_username(client: AsyncClient):
    user1 = await create_test_user(client, username="userone", email="userone@example.com")
    await create_test_user(client, username="usertwo", email="usertwo@example.com")
    token1 = await login_user(client, email="userone@example.com")

    response = await client.patch(
        f"/api/users/{user1['id']}",
        json={"username": "usertwo"},
        headers=auth_header(token1),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.anyio
async def test_update_user_profile_duplicate_email(client: AsyncClient):
    user1 = await create_test_user(client, username="userone", email="userone@example.com")
    await create_test_user(client, username="usertwo", email="usertwo@example.com")
    token1 = await login_user(client, email="userone@example.com")

    response = await client.patch(
        f"/api/users/{user1['id']}",
        json={"email": "usertwo@example.com"},
        headers=auth_header(token1),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


## -------------------------------------------------------------
## Password Management (Change & Reset)
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_change_password_success(client: AsyncClient):
    await create_test_user(
        client,
        username="pwduser",
        email="pwduser@example.com",
        password="oldpassword123",
    )
    token = await login_user(
        client, email="pwduser@example.com", password="oldpassword123"
    )

    response = await client.patch(
        "/api/users/me/password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

    # Verify new password works
    new_token = await login_user(
        client, email="pwduser@example.com", password="newpassword123"
    )
    assert new_token is not None


@pytest.mark.anyio
async def test_change_password_invalid_current_password(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    response = await client.patch(
        "/api/users/me/password",
        json={
            "current_password": "wrongpassword123",
            "new_password": "newpassword123",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


@pytest.mark.anyio
async def test_forgot_and_reset_password_flow(client: AsyncClient):
    await create_test_user(
        client,
        username="resetuser",
        email="resetuser@example.com",
        password="initialpassword123",
    )

    captured_token = None
    with patch(
        "routers.users.send_password_reset_email",
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            "/api/users/forgot-password",
            json={"email": "resetuser@example.com"},
        )
        assert response.status_code == 202
        mock_send.assert_awaited_once()
        captured_token = mock_send.call_args.kwargs["token"]

    assert captured_token is not None

    # Reset password using token
    reset_resp = await client.post(
        "/api/users/reset-password",
        json={
            "token": captured_token,
            "new_password": "resetcomplete123",
        },
    )
    assert reset_resp.status_code == 200
    assert "Password reset successfully" in reset_resp.json()["message"]

    # Verify login with new password succeeds
    login_resp = await client.post(
        "/api/users/token",
        data={
            "username": "resetuser@example.com",
            "password": "resetcomplete123",
        },
    )
    assert login_resp.status_code == 200

    # Old password no longer works
    old_login = await client.post(
        "/api/users/token",
        data={
            "username": "resetuser@example.com",
            "password": "initialpassword123",
        },
    )
    assert old_login.status_code == 401


@pytest.mark.anyio
async def test_reset_password_invalid_token(client: AsyncClient):
    response = await client.post(
        "/api/users/reset-password",
        json={
            "token": "invalid-or-fake-token-value",
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token"


## -------------------------------------------------------------
## Profile Picture & S3 Storage
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_profile_picture(client: AsyncClient, mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)

    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()

    response = await client.patch(
        f"/api/users/{user['id']}/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["image_file"] is not None
    assert data["image_file"].endswith(".jpg")
    assert "s3" in data["image_path"]

    s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
    assert "Contents" in s3_objects
    assert len(s3_objects["Contents"]) == 1
    assert s3_objects["Contents"][0]["Key"].endswith(data["image_file"])


@pytest.mark.anyio
async def test_upload_profile_picture_wrong_user(client: AsyncClient, mocked_aws):
    user1 = await create_test_user(client, username="picuser1", email="pic1@example.com")
    await create_test_user(client, username="picuser2", email="pic2@example.com")
    token2 = await login_user(client, email="pic2@example.com")

    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()

    response = await client.patch(
        f"/api/users/{user1['id']}/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers=auth_header(token2),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this user's picture"


@pytest.mark.anyio
async def test_delete_profile_picture_success(client: AsyncClient, mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    # 1. Upload picture first
    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()
    await client.patch(
        f"/api/users/{user['id']}/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers=headers,
    )

    # 2. Delete picture
    delete_resp = await client.delete(
        f"/api/users/{user['id']}/picture",
        headers=headers,
    )
    assert delete_resp.status_code == 200
    data = delete_resp.json()
    assert data["image_file"] is None

    # S3 bucket should now be empty of profile pictures
    s3_objects = mocked_aws.list_objects_v2(Bucket="test-bucket")
    assert "Contents" not in s3_objects


@pytest.mark.anyio
async def test_delete_profile_picture_no_picture(client: AsyncClient):
    user = await create_test_user(client)
    token = await login_user(client)

    response = await client.delete(
        f"/api/users/{user['id']}/picture",
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No profile picture to delete"


@pytest.mark.anyio
async def test_delete_profile_picture_wrong_user(client: AsyncClient):
    user1 = await create_test_user(client, username="p1", email="p1@example.com")
    await create_test_user(client, username="p2", email="p2@example.com")
    token2 = await login_user(client, email="p2@example.com")

    response = await client.delete(
        f"/api/users/{user1['id']}/picture",
        headers=auth_header(token2),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this user's picture"


## -------------------------------------------------------------
## User Account Deletion
## -------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_user_success(client: AsyncClient, mocked_aws):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    # Upload avatar before deleting user to test S3 file cleanup on delete
    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()
    await client.patch(
        f"/api/users/{user['id']}/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpeg")},
        headers=headers,
    )

    delete_resp = await client.delete(
        f"/api/users/{user['id']}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    # Subsequent login must fail
    login_resp = await client.post(
        "/api/users/token",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert login_resp.status_code == 401


@pytest.mark.anyio
async def test_delete_user_unauthorized(client: AsyncClient):
    user1 = await create_test_user(client, username="del1", email="del1@example.com")
    await create_test_user(client, username="del2", email="del2@example.com")
    token2 = await login_user(client, email="del2@example.com")

    delete_resp = await client.delete(
        f"/api/users/{user1['id']}",
        headers=auth_header(token2),
    )
    assert delete_resp.status_code == 401
    assert delete_resp.json()["detail"] == "Un-Authorized Action"
