from typing import List, Optional
from shared.schemas.finding_result import FindingResult, FindingState
from shared.models.enums import DiagnosticCode


def build_finding_result(
    job_id: str,
    state: FindingState,
    diagnostic_code: DiagnosticCode | str,
    message: str,
    symbolic_simplification: Optional[str] = None,
    dimensions_verified: bool = False,
    diagnostics: Optional[List[str]] = None,
) -> FindingResult:
    return FindingResult(
        job_id=job_id,
        state=state,
        diagnostic_code=str(diagnostic_code),
        message=message,
        symbolic_simplification=symbolic_simplification,
        dimensions_verified=dimensions_verified,
        diagnostics=diagnostics or [],
    )
