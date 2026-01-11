"""
Hello World API 测试
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_hello_world():
    """测试基本问候接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/hello")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "成功"
        assert "greeting" in data["data"]
        assert "english" in data["data"]


@pytest.mark.asyncio
async def test_hello_name():
    """测试个性化问候接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/hello/张三")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "张三" in data["data"]["greeting"]


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_root():
    """测试根路径接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "service" in data["data"]
        assert "version" in data["data"]
