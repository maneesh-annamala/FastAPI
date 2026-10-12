import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_user


# Posts Collection: GET & POST
@pytest.mark.anyio
async def test_get_posts_empty(client: AsyncClient):
    response = await client.get("/api/posts")
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert "total" in data
    assert "skip" in data
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["posts"] == []
    assert data["has_more"] is False
    assert isinstance(data["posts"], list)


@pytest.mark.anyio
async def test_create_post_success(client: AsyncClient):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title": "My First Post", "content": "This is the content"},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My First Post"
    assert data["content"] == "This is the content"
    assert data["user_id"] == user["id"]
    assert "id" in data
    assert "date_posted" in data
    assert data["author"]["username"] == "testuser"


@pytest.mark.anyio
async def test_create_post_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/posts",
        json={"title": "Test Post", "content": "Test content"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_get_posts_with_pagination(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    for i in range(5):
        response = await client.post(
            "/api/posts",
            json={"title": f"Post {i}", "content": f"Content for post {i}"},
            headers=headers,
        )
        assert response.status_code == 201

    response = await client.get("/api/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 5
    assert data["has_more"] is False

    response = await client.get("/api/posts?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 2
    assert data["has_more"] is True

    response = await client.get("/api/posts?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 2
    assert data["skip"] == 2
    assert data["limit"] == 2
    assert data["has_more"] is True


# Single Post: GET
@pytest.mark.anyio
async def test_get_single_post_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    create_resp = await client.post(
        "/api/posts",
        json={"title": "Single Post Title", "content": "Single post content body"},
        headers=headers,
    )
    post_id = create_resp.json()["id"]

    response = await client.get(f"/api/posts/{post_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["title"] == "Single Post Title"
    assert data["content"] == "Single post content body"
    assert data["author"]["username"] == "testuser"


@pytest.mark.anyio
async def test_get_single_post_not_found(client: AsyncClient):
    response = await client.get("/api/posts/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


# Update Post: PATCH (Partial) & PUT (Full)
@pytest.mark.anyio
async def test_update_post_partial_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title": "Original Title", "content": "Original content"},
        headers=headers,
    )
    post_id = response.json()["id"]

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title": "Updated Title"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Original content"


@pytest.mark.anyio
async def test_update_post_partial_wrong_user(client: AsyncClient):
    await create_test_user(client, username="user1", email="user1@example.com")
    token1 = await login_user(client, email="user1@example.com")

    response = await client.post(
        "/api/posts",
        json={"title": "User 1's Post", "content": "Only user 1 can edit this"},
        headers=auth_header(token1),
    )
    post_id = response.json()["id"]

    await create_test_user(client, username="user2", email="user2@example.com")
    token2 = await login_user(client, email="user2@example.com")

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title": "Hacked Title"},
        headers=auth_header(token2),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not authorized to update this post"


@pytest.mark.anyio
async def test_update_post_partial_not_found(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    response = await client.patch(
        "/api/posts/999999",
        json={"title": "Ghost Title"},
        headers=auth_header(token),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


@pytest.mark.anyio
async def test_update_post_full_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title": "Old Full Title", "content": "Old full content"},
        headers=headers,
    )
    post_id = response.json()["id"]

    response = await client.put(
        f"/api/posts/{post_id}",
        json={"title": "New Full Title", "content": "New full content here"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Full Title"
    assert data["content"] == "New full content here"


@pytest.mark.anyio
async def test_update_post_full_wrong_user(client: AsyncClient):
    await create_test_user(client, username="author1", email="author1@example.com")
    token1 = await login_user(client, email="author1@example.com")

    response = await client.post(
        "/api/posts",
        json={"title": "Author 1 Post", "content": "Author 1 original text"},
        headers=auth_header(token1),
    )
    post_id = response.json()["id"]

    await create_test_user(client, username="author2", email="author2@example.com")
    token2 = await login_user(client, email="author2@example.com")

    response = await client.put(
        f"/api/posts/{post_id}",
        json={"title": "Replaced Title", "content": "Replaced content text"},
        headers=auth_header(token2),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "user didn't matched"


@pytest.mark.anyio
async def test_update_post_full_not_found(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    response = await client.put(
        "/api/posts/999999",
        json={"title": "Ghost Post", "content": "Ghost content here"},
        headers=auth_header(token),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


# Delete Post: DELETE
@pytest.mark.anyio
async def test_delete_post_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title": "Post To Delete", "content": "This post will be deleted"},
        headers=headers,
    )
    post_id = response.json()["id"]

    delete_resp = await client.delete(f"/api/posts/{post_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Verify post is gone
    get_resp = await client.get(f"/api/posts/{post_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_post_wrong_user(client: AsyncClient):
    await create_test_user(client, username="owner", email="owner@example.com")
    token_owner = await login_user(client, email="owner@example.com")

    response = await client.post(
        "/api/posts",
        json={"title": "Owner's Post", "content": "Content of the post"},
        headers=auth_header(token_owner),
    )
    post_id = response.json()["id"]

    await create_test_user(client, username="intruder", email="intruder@example.com")
    token_intruder = await login_user(client, email="intruder@example.com")

    delete_resp = await client.delete(
        f"/api/posts/{post_id}",
        headers=auth_header(token_intruder),
    )
    assert delete_resp.status_code == 403
    assert delete_resp.json()["detail"] == "User didn't Matched"


@pytest.mark.anyio
async def test_delete_post_not_found(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    delete_resp = await client.delete(
        "/api/posts/999999",
        headers=auth_header(token),
    )
    assert delete_resp.status_code == 404
    assert delete_resp.json()["detail"] == "Post not found"


@pytest.mark.anyio
async def test_create_comment_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Comments", "content": "Content of the post for comment testing"},
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "This is a great post!"},
        headers=headers,
    )
    assert comment_resp.status_code == 201
    data = comment_resp.json()
    assert data["comment"] == "This is a great post!"
    assert data["post_id"] == post_id
    assert data["comment_author"]["username"] == "testuser"
    assert "date_commented" in data


@pytest.mark.anyio
async def test_create_comment_unauthorized(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Comments", "content": "Content of the post for comment testing"},
        headers=auth_header(token),
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Anonymous comment"},
    )
    assert comment_resp.status_code == 401


@pytest.mark.anyio
async def test_create_comment_post_not_found(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    comment_resp = await client.post(
        "/api/posts/999999/comments",
        json={"comment": "Ghost comment"},
        headers=auth_header(token),
    )
    assert comment_resp.status_code == 404
    assert comment_resp.json()["detail"] == "Post not found"


@pytest.mark.anyio
async def test_get_single_post_includes_comments(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post with Comments", "content": "Testing comments retrieval in post"},
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "First comment"},
        headers=headers,
    )
    await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Second comment"},
        headers=headers,
    )

    get_resp = await client.get(f"/api/posts/{post_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data["comments"]) == 2
    assert data["comments"][0]["comment"] == "First comment"
    assert data["comments"][1]["comment"] == "Second comment"


@pytest.mark.anyio
async def test_update_comment_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Edit Comment", "content": "Post body content"},
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Original comment"},
        headers=headers,
    )
    comment_id = comment_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/posts/{post_id}/comments/{comment_id}",
        json={"comment": "Updated comment"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["comment"] == "Updated comment"


@pytest.mark.anyio
async def test_update_comment_wrong_user(client: AsyncClient):
    await create_test_user(client, username="author", email="author@example.com")
    token_author = await login_user(client, email="author@example.com")

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Edit Comment", "content": "Post body content"},
        headers=auth_header(token_author),
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Author's comment"},
        headers=auth_header(token_author),
    )
    comment_id = comment_resp.json()["id"]

    await create_test_user(client, username="otheruser", email="other@example.com")
    token_other = await login_user(client, email="other@example.com")

    patch_resp = await client.patch(
        f"/api/posts/{post_id}/comments/{comment_id}",
        json={"comment": "Hijacked comment"},
        headers=auth_header(token_other),
    )
    assert patch_resp.status_code == 403
    assert patch_resp.json()["detail"] == "User didn't Matched"


@pytest.mark.anyio
async def test_delete_comment_success(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Delete Comment", "content": "Post body content"},
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Comment to delete"},
        headers=headers,
    )
    comment_id = comment_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/posts/{post_id}/comments/{comment_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/posts/{post_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["comments"]) == 0


@pytest.mark.anyio
async def test_delete_comment_wrong_user(client: AsyncClient):
    await create_test_user(client, username="cauthor", email="cauthor@example.com")
    token_cauthor = await login_user(client, email="cauthor@example.com")

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post for Delete Comment", "content": "Post body content"},
        headers=auth_header(token_cauthor),
    )
    post_id = post_resp.json()["id"]

    comment_resp = await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Comment to delete"},
        headers=auth_header(token_cauthor),
    )
    comment_id = comment_resp.json()["id"]

    await create_test_user(client, username="intruder2", email="intruder2@example.com")
    token_intruder = await login_user(client, email="intruder2@example.com")

    del_resp = await client.delete(
        f"/api/posts/{post_id}/comments/{comment_id}",
        headers=auth_header(token_intruder),
    )
    assert del_resp.status_code == 403
    assert del_resp.json()["detail"] == "User didn't Matched"


@pytest.mark.anyio
async def test_delete_post_cascades_comments(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    post_resp = await client.post(
        "/api/posts",
        json={"title": "Post Cascade Test", "content": "Post body content for cascade"},
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Comment 1 to cascade"},
        headers=headers,
    )
    await client.post(
        f"/api/posts/{post_id}/comments",
        json={"comment": "Comment 2 to cascade"},
        headers=headers,
    )

    del_resp = await client.delete(f"/api/posts/{post_id}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/posts/{post_id}")
    assert get_resp.status_code == 404
