import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.research_core.exporter import (
    BundleSigningUnavailableError,
    generate_research_zip_bundle,
)
from app.modules.research_core.schemas import ProjectCreate, ProjectResponse
from app.modules.research_core.service import create_project, get_project_by_slug
from app.modules.iam_governance.dependencies import (
    get_current_actor,
    get_optional_current_actor,
)
from app.modules.iam_governance.models import ResearchActor

projects_router = APIRouter(prefix="/projects", tags=["projects"])
versions_router = APIRouter(prefix="/versions", tags=["versions"])


@projects_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    payload: ProjectCreate,
    actor: ResearchActor = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    return await create_project(db, actor.id, payload)


@projects_router.get("/{slug}", response_model=ProjectResponse)
async def get_project(
    slug: str,
    actor: ResearchActor | None = Depends(get_optional_current_actor),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    project = await get_project_by_slug(db, slug)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.visibility == "private_draft" and (actor is None or actor.id != project.owner_actor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@versions_router.post("/{version_id}/export-zip")
async def export_version_zip(
    version_id: str,
    actor: ResearchActor | None = Depends(get_optional_current_actor),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Generates and streams an immutable Open Research Cryptographic ZIP bundle.

    Rejects unfrozen drafts with HTTP 400 'CANNOT_EXPORT_UNFROZEN_DRAFT'.
    Enforces project visibility and owner access controls.
    """
    try:
        zip_bytes = await generate_research_zip_bundle(
            version_id=version_id,
            db=db,
            current_actor_id=actor.id if actor else None,
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "CANNOT_EXPORT_UNFROZEN_DRAFT" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CANNOT_EXPORT_UNFROZEN_DRAFT",
            )
        elif "Version not found" in err_msg or "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg,
            )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    except BundleSigningUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research bundle signing is unavailable because its signing configuration is invalid.",
        ) from error

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="research_bundle_{version_id}.zip"',
            "Content-Type": "application/zip",
        },
    )


# Combined composite router mounted into /api/v1
router = APIRouter()
router.include_router(projects_router)
router.include_router(versions_router)

__all__ = ["projects_router", "router", "versions_router"]
