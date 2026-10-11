import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_user


@pytest.mark.anyio
async def test_home_page(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.anyio
async def test_posts_page(client: AsyncClient):
    response = await client.get("/posts")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.anyio
async def test_post_detail_page_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Template Test Post", "content": "Template content for page"},
        headers=auth_header(token),
    )
    post_id = post_resp.json()["id"]

    response = await client.get(f"/posts/{post_id}")
    assert response.status_code == 200
    assert "Template Test Post" in response.text


@pytest.mark.anyio
async def test_post_detail_page_not_found(client: AsyncClient):
    response = await client.get("/posts/999999")
    assert response.status_code == 404
    assert "Post not found" in response.text


@pytest.mark.anyio
async def test_user_posts_page_success(client: AsyncClient):
    user = await create_test_user(client, username="blogger", email="blogger@example.com")
    token = await login_user(client, email="blogger@example.com")

    await client.post(
        "/api/posts",
        json={"title": "Blogger's First Post", "content": "Blogger content body"},
        headers=auth_header(token),
    )

    response = await client.get(f"/users/{user['id']}/posts")
    assert response.status_code == 200
    assert "blogger" in response.text


@pytest.mark.anyio
async def test_user_posts_page_not_found(client: AsyncClient):
    response = await client.get("/users/999999/posts")
    assert response.status_code == 404
    assert "User not found" in response.text


@pytest.mark.anyio
async def test_login_page(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text


@pytest.mark.anyio
async def test_register_page(client: AsyncClient):
    response = await client.get("/register")
    assert response.status_code == 200
    assert "Register" in response.text


@pytest.mark.anyio
async def test_account_page(client: AsyncClient):
    response = await client.get("/account")
    assert response.status_code == 200
    assert "Account" in response.text


@pytest.mark.anyio
async def test_forgot_password_page(client: AsyncClient):
    response = await client.get("/forgot-password")
    assert response.status_code == 200
    assert "Forgot Password" in response.text


@pytest.mark.anyio
async def test_reset_password_page(client: AsyncClient):
    response = await client.get("/reset-password")
    assert response.status_code == 200
    assert "Reset Password" in response.text
    assert response.headers.get("referrer-policy") == "no-referrer"
