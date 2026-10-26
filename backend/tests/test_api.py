"""Vulture Bot - API Integration Tests."""

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import Base, get_engine


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert "Vulture Bot" in data["app"]


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/system/health")
        assert res.status_code == 200
        data = res.json()
        assert data["database_connected"] is True


@pytest.mark.asyncio
async def test_demo_login_and_authenticated_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sign in as admin
        login_res = await client.post(
            "/api/auth/demo-login",
            json={"email": "admin@vulture.local", "name": "Admin Tester", "is_admin": True},
        )
        assert login_res.status_code == 200
        token = login_res.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get profile
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        profile = me_res.json()
        assert profile["email"] == "admin@vulture.local"
        assert profile["is_admin"] is True

        # 3. Create a conversation
        conv_res = await client.post(
            "/api/conversations",
            json={"title": "Test AI Chat"},
            headers=headers,
        )
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # 4. Fetch conversations list
        list_res = await client.get("/api/conversations", headers=headers)
        assert list_res.status_code == 200
        convs = list_res.json()
        assert any(c["id"] == conv_id for c in convs)
