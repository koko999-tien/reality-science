from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.research_core.schemas import ProjectCreate, ProjectResponse
from app.modules.research_core.service import create_project, get_project_by_slug

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    payload: ProjectCreate,
    owner_actor_id: str = "default_actor",
    db: AsyncSession = Depends(get_db),
):
    return await create_project(db, owner_actor_id, payload)


@router.get("/{slug}", response_model=ProjectResponse)
async def get_project(slug: str, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_slug(db, slug)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
