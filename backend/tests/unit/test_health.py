"""Unit tests for Backend Service Health Check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_health_endpoint():
    """Verify GET /health returns status, version, and component status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.version
    assert data["service"] == "reality-science-api"
    assert "components" in data
    assert data["components"]["api"] == "healthy"
    assert data["components"]["database"] == "configured"
    assert data["components"]["redis"] == "configured"
    assert data["components"]["compute_worker_conduit"] == "ready"


@pytest.mark.asyncio
async def test_health_db_check_unreachable():
    """Verify GET /health/db returns 503 when database is unreachable."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/db")

    # In local test environment without PostgreSQL daemon, /health/db correctly returns 503
    assert response.status_code == 503
    data = response.json()
    assert "Database unreachable" in data["detail"]


@pytest.mark.asyncio
async def test_health_redis_check_unreachable():
    """Verify GET /health/redis returns 503 when Redis is unreachable."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/redis")

    # In local test environment without Redis daemon, /health/redis correctly returns 503
    assert response.status_code == 503
    data = response.json()
    assert "Redis unreachable" in data["detail"]
