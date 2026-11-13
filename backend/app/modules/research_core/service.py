from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.research_core.models import ResearchProject
from app.modules.research_core.schemas import ProjectCreate


async def create_project(db: AsyncSession, owner_actor_id: str, payload: ProjectCreate) -> ResearchProject:
    project = ResearchProject(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        owner_actor_id=owner_actor_id,
        visibility=payload.visibility,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project_by_slug(db: AsyncSession, slug: str) -> ResearchProject | None:
    stmt = select(ResearchProject).where(ResearchProject.slug == slug)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
