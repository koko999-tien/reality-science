from celery.exceptions import SoftTimeLimitExceeded

from shared.models.enums import DiagnosticCode
from shared.schemas.epistemic_logic import ClaimGraph, ClaimGraphValidationResult
from shared.schemas.finding_result import FindingResult, FindingState
from worker.celery_app import celery_app
from worker.core.epistemic_engine import verify_claim_graph


@celery_app.task(name="worker.tasks.verify_epistemic_graph", bind=True)
def verify_epistemic_graph(self, graph_data: dict) -> dict:
    """Executes Layer 6 Epistemic Logic Verification (Circularity, Contradictions, Status Propagation)
    on an in-memory ClaimGraph without database access.
    """
    try:
        # graph_data can be ClaimGraph or JobBundle with claim_graph
        if "claim_graph" in graph_data and graph_data["claim_graph"] is not None:
            graph = ClaimGraph.model_validate(graph_data["claim_graph"])
            job_id = graph_data.get("job_id", graph.graph_id)
        else:
            graph = ClaimGraph.model_validate(graph_data)
            job_id = graph.graph_id

        res = verify_claim_graph(graph)

        # Select representative diagnostic code
        if res.cycle_report.cycle_detected:
            diag_code = DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value
            msg = f"Circular dependency detected in claim graph: {len(res.cycle_report.cycles)} cycle(s)."
        elif res.contradiction_report.contradictions_found:
            diag_code = DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value
            msg = f"Cross-claim contradiction detected in claim graph: {len(res.contradiction_report.items)} conflict(s)."
        elif res.overall_state == FindingState.FAIL:
            diag_code = DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value
            msg = "Antecedent failure poisoned dependent claims."
        elif res.overall_state == FindingState.WARNING:
            diag_code = DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value
            msg = "Epistemic graph verified with antecedent warning(s)."
        elif res.overall_state in (FindingState.INSUFFICIENT_DATA, FindingState.NOT_YET_TESTED):
            diag_code = DiagnosticCode.EPISTEMIC_DEPENDENCY_UNRESOLVED.value
            msg = "Epistemic graph has unresolved antecedent dependencies."
        else:
            diag_code = DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
            msg = "Epistemic logic graph successfully verified with zero cycles and zero contradictions."

        finding = FindingResult(
            job_id=job_id,
            state=res.overall_state,
            diagnostic_code=diag_code,
            message=msg,
            dimensions_verified=True,
            diagnostics=res.diagnostics,
            details=res.model_dump(),
            layer=6,
        )
        return finding.model_dump()
    except SoftTimeLimitExceeded:
        finding = FindingResult(
            job_id=graph_data.get("job_id", "timeout"),
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.COMPUTE_TIMEOUT_EXCEEDED.value,
            message="Epistemic graph verification exceeded time limit",
            layer=6,
        )
        return finding.model_dump()
    except Exception as exc:
        finding = FindingResult(
            job_id=graph_data.get("job_id", "error"),
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.INVALID_AST.value,
            message=f"Epistemic verification failed: {str(exc)}",
            layer=6,
        )
        return finding.model_dump()
