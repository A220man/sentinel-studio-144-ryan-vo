import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_login_returns_auth_url(client: AsyncClient):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "state" in data
    assert "code_verifier" in data
    assert "keycloak" in data["auth_url"]


@pytest.mark.asyncio
async def test_callback_missing_params(client: AsyncClient):
    response = await client.post("/auth/callback", json={})
    assert response.status_code == 422  # FastAPI validation error




@pytest.mark.asyncio
async def test_callback_exchanges_code(client: AsyncClient):
    response = await client.post(
        "/auth/callback",
        json={
            "code": "test-code",
            "state": "test-state",
            "code_verifier": "test-verifier",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, test_user, auth_headers):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user, auth_headers):
    from app.core.security import create_refresh_token
    refresh = create_refresh_token({"sub": str(test_user.id), "email": test_user.email, "username": test_user.username, "roles": [test_user.role.value]})

    response = await client.post(
        "/auth/refresh",
        headers=auth_headers,
        cookies={"refresh_token": refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user, auth_headers):
    response = await client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401