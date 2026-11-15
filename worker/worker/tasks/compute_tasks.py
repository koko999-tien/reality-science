from celery.exceptions import SoftTimeLimitExceeded
from worker.celery_app import celery_app
from shared.schemas.job_bundle import JobBundle
from shared.schemas.finding_result import FindingResult, FindingState
from shared.models.enums import DiagnosticCode
from worker.core.semantic_validator import validate_ast_semantics
from worker.core.boundary_engine import analyze_boundary_and_singularities
from worker.tasks.dimensional import execute_dimensional_verification


@celery_app.task(name="worker.tasks.verify_equation_ast", bind=True)
def verify_equation_ast(self, bundle_data: dict) -> dict:
    """Executes sequential Layer 1 (Syntax & Semantics), Layer 2 (Boundary & Singularity),
    and Layer 3 (Dimension) validation pipeline.
    """
    bundle = JobBundle.model_validate(bundle_data)
    try:
        # Layer 1: Definition, Complexity, & Semantic Checks
        l1_res = validate_ast_semantics(bundle.expression_ast, bundle.variables, bundle.units)
        if not l1_res.is_valid:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=l1_res.diagnostic_code,
                message=l1_res.message,
                dimensions_verified=False,
                diagnostics=l1_res.diagnostics,
            )
            return finding.model_dump()

        # Layer 2: Boundary & Singularity Solver + Symbolic Consistency
        l2_res = analyze_boundary_and_singularities(bundle.expression_ast, bundle.variables)
        if not l2_res.is_valid:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=l2_res.state,
                diagnostic_code=l2_res.diagnostic_code,
                message=l2_res.message,
                dimensions_verified=False,
                diagnostics=l2_res.diagnostics,
            )
            return finding.model_dump()

        # Layer 3: Dimensional SI Homogeneity & Transcendental Checks
        dim_ok, dim_str, dim_diag = execute_dimensional_verification(
            bundle.expression_ast, bundle.variables, bundle.units
        )
        if not dim_ok:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=dim_diag,
                message=f"Dimensional consistency check failed: {dim_diag}",
                dimensions_verified=False,
                diagnostics=[f"Dimensional verification failure: {dim_diag}"],
            )
            return finding.model_dump()

        # Sequential Verification Completed
        diagnostics = [
            f"Layer 1 Syntax: OK ({len(l1_res.referenced_symbols)} symbols)",
            f"Layer 2 Boundary: OK ({l2_res.simplified_expr})",
            f"Layer 3 Dimension: OK ({dim_str})",
            *l2_res.diagnostics,
        ]

        if l2_res.state == FindingState.WARNING:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.WARNING,
                diagnostic_code=l2_res.diagnostic_code,
                message=l2_res.message,
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
            )
        else:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.PASS,
                diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
                message="Mathematical AST passed semantic, boundary/singularity, and dimensional checks.",
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
            )
        return finding.model_dump()

    except SoftTimeLimitExceeded:
        finding = FindingResult(
            job_id=bundle.job_id,
            state=FindingState.NEEDS_EXPERT_REVIEW,
            diagnostic_code=DiagnosticCode.COMPUTE_TIMEOUT_EXCEEDED.value,
            message="Computation exceeded maximum allowed execution time.",
            dimensions_verified=False,
            diagnostics=["Soft time limit exceeded during symbolic computation"],
        )
        return finding.model_dump()
    except Exception as e:
        finding = FindingResult(
            job_id=bundle.job_id,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.INVALID_AST.value,
            message=f"Computation encountered unexpected error: {str(e)}",
            dimensions_verified=False,
            diagnostics=[str(e)],
        )
        return finding.model_dump()
