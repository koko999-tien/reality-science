from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.reality_constraint_engine.models import ValidationRun, ValidationFinding
from shared.schemas.finding_result import FindingResult


async def record_validation_finding(
    db: AsyncSession, run_id: str, finding: FindingResult
) -> ValidationFinding:
    vf = ValidationFinding(
        run_id=run_id,
        job_id=finding.job_id,
        state=str(finding.state),
        diagnostic_code=str(finding.diagnostic_code),
        message=finding.message,
        symbolic_simplification=finding.symbolic_simplification,
        dimensions_verified=finding.dimensions_verified,
        diagnostics={"details": finding.diagnostics},
    )
    db.add(vf)
    await db.commit()
    await db.refresh(vf)
    return vf
