from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token_subject
from app.db.session import get_db
from app.modules.iam_governance.models import ResearchActor, UserAccount
from app.modules.research_core.models import ResearchProject, ResearchVersion

bearer_scheme = HTTPBearer(auto_error=False)


@event.listens_for(Session, "after_begin")
def _apply_research_actor_context(session: Session, transaction, connection) -> None:
    actor_context = session.info.get("research_actor_context")
    if actor_context is None:
        return
    actor_id, organization_id = actor_context
    connection.execute(
        text("SELECT set_config('app.current_actor_id', :actor_id, true)"),
        {"actor_id": actor_id},
    )
    connection.execute(
        text("SELECT set_config('app.current_org_id', :organization_id, true)"),
        {"organization_id": organization_id},
    )


async def _set_actor_context(db: AsyncSession, actor: ResearchActor) -> None:
    db.info["research_actor_context"] = (actor.id, actor.organization_id or "")
    await db.execute(
        text("SELECT set_config('app.current_actor_id', :actor_id, true)"),
        {"actor_id": actor.id},
    )
    await db.execute(
        text("SELECT set_config('app.current_org_id', :organization_id, true)"),
        {"organization_id": actor.organization_id or ""},
    )


async def resolve_current_actor(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> ResearchActor | None:
    if credentials is None:
        return None
    user_id = decode_access_token_subject(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(UserAccount)
        .options(selectinload(UserAccount.actor))
        .where(UserAccount.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await _set_actor_context(db, user.actor)
    return user.actor


async def get_current_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchActor:
    actor = await resolve_current_actor(credentials, db)
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return actor


async def get_optional_current_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchActor | None:
    return await resolve_current_actor(credentials, db)


async def get_accessible_version(
    version_id: str,
    actor: Annotated[ResearchActor | None, Depends(get_optional_current_actor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchVersion:
    result = await db.execute(select(ResearchVersion).where(ResearchVersion.id == version_id))
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    project_result = await db.execute(select(ResearchProject).where(ResearchProject.id == version.project_id))
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    if project.visibility == "private_draft" and (actor is None or actor.id != project.owner_actor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


async def get_owned_version(
    version_id: str,
    actor: Annotated[ResearchActor, Depends(get_current_actor)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchVersion:
    version = await get_accessible_version(version_id=version_id, actor=actor, db=db)
    project_result = await db.execute(select(ResearchProject).where(ResearchProject.id == version.project_id))
    project = project_result.scalar_one_or_none()
    if project is None or project.owner_actor_id != actor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version
