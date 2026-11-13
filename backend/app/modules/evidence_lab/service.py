from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.evidence_lab.models import EvidenceArtifact


async def register_evidence_artifact(
    db: AsyncSession, project_id: str, storage_path: str, sha256_hash: str, description: str = ""
) -> EvidenceArtifact:
    artifact = EvidenceArtifact(
        project_id=project_id,
        storage_path=storage_path,
        sha256_hash=sha256_hash,
        description=description,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact
