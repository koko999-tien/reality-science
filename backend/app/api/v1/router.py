from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.research_core.router import router as research_core_router
from app.modules.evidence_lab.router import router as evidence_router
from app.modules.cluster_orchestrator.router import router as cluster_router
from app.modules.reality_constraint_engine.router import router as rce_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(research_core_router)
api_router.include_router(evidence_router)
api_router.include_router(cluster_router)
api_router.include_router(rce_router)

