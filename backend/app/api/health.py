"""Root health check API router for REALITY SCIENCE Backend (Zone 2).

Provides root /health endpoint reporting service status, version, and component status.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.core.redis import get_redis_client

health_router = APIRouter(tags=["health"])


@health_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Root health check endpoint reporting status, version, and component status."""
    return {
        "status": "healthy",
        "service": "reality-science-api",
        "version": settings.version,
        "environment": settings.environment,
        "components": {
            "api": "healthy",
            "database": "configured",
            "redis": "configured",
            "compute_worker_conduit": "ready",
        },
    }


@health_router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_db_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Database connectivity health check."""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "component": "database",
            "database": "postgresql",
            "details": "connected",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(e)}",
        )


@health_router.get("/health/redis", status_code=status.HTTP_200_OK)
async def health_redis_check() -> Dict[str, Any]:
    """Redis conduit connectivity health check."""
    try:
        redis = await get_redis_client()
        pong = await redis.ping()
        return {
            "status": "healthy",
            "component": "redis",
            "redis": pong,
            "details": "connected",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis unreachable: {str(e)}",
        )
