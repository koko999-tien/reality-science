from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.redis import get_redis_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok", "service": "reality-science-api"}


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_db_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "postgresql"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {str(e)}",
        )


@router.get("/redis", status_code=status.HTTP_200_OK)
async def health_redis_check():
    try:
        redis = await get_redis_client()
        pong = await redis.ping()
        return {"status": "ok", "redis": pong}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis unreachable: {str(e)}",
        )
