from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.health import health_router
from app.api.v1.router import api_router
from app.core.redis import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    yield
    await close_redis_client()


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

if settings.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
