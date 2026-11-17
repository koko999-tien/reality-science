"""Owner-managed working mathematics; one transaction per snapshot replacement."""
from fastapi import HTTPException
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.reality_constraint_engine.models import Equation, Variable
from app.modules.research_core.models import ResearchProject, ResearchVersion
from app.modules.research_core.schemas import DraftSave, DraftSnapshot, VersionCreate
from app.modules.research_core.events import record_draft_event


async def create_version(db: AsyncSession, slug: str, actor_id: str, payload: VersionCreate):
    try:
        # Project lock serializes numbering even when no versions exist yet.
        project = (await db.execute(select(ResearchProject).where(
            ResearchProject.slug == slug, ResearchProject.owner_actor_id == actor_id
        ).with_for_update())).scalar_one_or_none()
        if project is None:
            raise HTTPException(404, "Project not found")
        if project.is_frozen:
            raise HTTPException(409, "CANNOT_MODIFY_FROZEN_PROJECT")
        if project.visibility != "private_draft":
            raise HTTPException(409, "DRAFT_REQUIRES_PRIVATE_PROJECT")
        maximum = (await db.execute(select(func.max(ResearchVersion.version_number)).where(
            ResearchVersion.project_id == project.id))).scalar_one()
        version = ResearchVersion(project_id=project.id, version_number=(maximum or 0) + 1,
                                  title=payload.title)
        db.add(version)
        await db.flush()
        snapshot = await read_draft(db, version.id)
        await record_draft_event(db, version.id, "ResearchDraftCreated", None, snapshot.model_dump(mode="json"))
        await db.commit()
        return version
    except Exception:
        await db.rollback()
        raise


async def read_draft(db: AsyncSession, version_id: str) -> DraftSnapshot:
    # One PostgreSQL statement = one MVCC snapshot for revision + every child table.
    # Separate SELECTs under READ COMMITTED can mix pre-save and post-save rows.
    row = (await db.execute(text("""
        SELECT row_to_json(v) AS version,
            (SELECT COALESCE(json_agg(e ORDER BY e.position NULLS LAST, e.created_at, e.id), '[]')
             FROM equations e WHERE e.version_id = v.id) AS equations,
            (SELECT COALESCE(json_agg(x ORDER BY x.created_at, x.id), '[]')
             FROM variables x WHERE x.version_id = v.id) AS variables
        FROM research_versions v WHERE v.id = :id
    """), {"id": version_id})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Version not found")
    return DraftSnapshot(version=row["version"], equations=row["equations"],
                         variables=row["variables"], units=row["version"]["units_json"])


async def save_draft(db: AsyncSession, version_id: str, payload: DraftSave) -> DraftSnapshot:
    try:
        # Stabilize ownership and project mutability before locking the version.
        # This shares the project -> version lock order with version creation.
        actor_id = db.info["research_actor_context"][0]
        project = (await db.execute(select(ResearchProject).options(noload("*")).where(
            ResearchProject.id == select(ResearchVersion.project_id).where(
                ResearchVersion.id == version_id).scalar_subquery(),
            ResearchProject.owner_actor_id == actor_id,
        ).with_for_update(read=True).execution_options(populate_existing=True))).scalar_one_or_none()
        if project is None:
            raise HTTPException(404, "Version not found")
        if project.is_frozen:
            raise HTTPException(409, "CANNOT_MODIFY_FROZEN_PROJECT")
        version = (await db.execute(select(ResearchVersion).options(noload("*")).where(
            ResearchVersion.id == version_id).with_for_update()
            .execution_options(populate_existing=True))).scalar_one_or_none()
        if version is None:
            raise HTTPException(404, "Version not found")
        if version.is_frozen:
            raise HTTPException(409, "CANNOT_MODIFY_FROZEN_VERSION")
        if version.publication_status != "draft" or version.content_hash is not None:
            raise HTTPException(409, "VERSION_IS_NOT_AN_UNSEALED_DRAFT")
        if version.revision != payload.expected_revision:
            raise HTTPException(409, {"code": "DRAFT_REVISION_CONFLICT",
                                      "current_revision": version.revision})
        before = await read_draft(db, version_id)

        existing = list((await db.execute(select(Equation).where(Equation.version_id == version_id))).scalars())
        by_id = {e.id: e for e in existing}
        supplied = {e.id for e in payload.equations if e.id}
        if not supplied.issubset(by_id):
            raise HTTPException(422, "Equation ID does not belong to this version")

        # Advance once even for an empty save; child triggers may advance further.
        # The revision is an opaque monotonic concurrency token, not a save count.
        version.revision += 1
        version.units_json = [u.model_dump(mode="json") for u in payload.units]
        await db.flush()
        for old in existing:
            if old.id not in supplied:
                await db.delete(old)
        for position, item in enumerate(payload.equations):
            equation = by_id.get(item.id)
            if equation is None:
                equation = Equation(version_id=version_id)
                db.add(equation)
            equation.label = item.label
            equation.position = position
            equation.latex_raw = item.latex_raw
            equation.canonical_ast_json = item.canonical_ast_json.model_dump(mode="json", exclude_none=True)
            equation.sympy_expr = None  # derived from the previous AST, never reusable
        await db.execute(delete(Variable).where(Variable.version_id == version_id))
        for item in payload.variables:
            db.add(Variable(version_id=version_id, **item.model_dump()))
        await db.flush()
        snapshot = await read_draft(db, version_id)
        await record_draft_event(db, version_id, "ResearchDraftSaved", before.model_dump(mode="json"), snapshot.model_dump(mode="json"))
        await db.commit()
        return snapshot
    except Exception:
        await db.rollback()
        raise
