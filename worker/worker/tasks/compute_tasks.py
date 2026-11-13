from celery.exceptions import SoftTimeLimitExceeded
from worker.celery_app import celery_app
from shared.schemas.job_bundle import JobBundle
from shared.schemas.finding_result import FindingResult, FindingState
from shared.models.enums import DiagnosticCode
from worker.tasks.symbolic import execute_symbolic_evaluation
from worker.tasks.dimensional import execute_dimensional_verification
from worker.core.complexity_guard import (
    inspect_ast_complexity,
    ComplexityLimitExceededError,
)


@celery_app.task(name="worker.tasks.verify_equation_ast", bind=True)
def verify_equation_ast(self, bundle_data: dict) -> dict:
    bundle = JobBundle.model_validate(bundle_data)
    try:
        declared_symbols = {v.symbol for v in bundle.variables}

        # 0. Pre-flight AST complexity guard (defense against recursion/power DoS)
        try:
            inspect_ast_complexity(bundle.expression_ast)
        except ComplexityLimitExceededError as e:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code="COMPLEXITY_LIMIT_EXCEEDED",
                message=str(e),
                dimensions_verified=False,
                diagnostics=[str(e)],
            )
            return finding.model_dump()

        # 1. Dimensional verification
        dim_ok, dim_str, dim_diag = execute_dimensional_verification(
            bundle.expression_ast, bundle.variables, bundle.units
        )
        if not dim_ok:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=dim_diag,
                message="Dimensional consistency check failed.",
                dimensions_verified=False,
                diagnostics=[f"Dimensional verification failure: {dim_diag}"],
            )
            return finding.model_dump()

        # 2. Symbolic evaluation
        sym_ok, sym_expr, sym_diag = execute_symbolic_evaluation(
            bundle.expression_ast, declared_symbols
        )
        if not sym_ok:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=sym_diag,
                message="Symbolic evaluation failed.",
                dimensions_verified=True,
                diagnostics=[f"Symbolic evaluation failure: {sym_diag}"],
            )
            return finding.model_dump()

        # 3. Successful verification
        finding = FindingResult(
            job_id=bundle.job_id,
            state=FindingState.PASS,
            diagnostic_code=str(DiagnosticCode.VALIDATION_PASSED),
            message="Mathematical AST passed symbolic simplification and dimensional checks.",
            symbolic_simplification=sym_expr,
            dimensions_verified=True,
            diagnostics=[f"Dimensionality: {dim_str}"],
        )
        return finding.model_dump()

    except SoftTimeLimitExceeded:
        finding = FindingResult(
            job_id=bundle.job_id,
            state=FindingState.NEEDS_EXPERT_REVIEW,
            diagnostic_code=str(DiagnosticCode.COMPUTE_TIMEOUT_EXCEEDED),
            message="Computation exceeded maximum allowed execution time.",
            dimensions_verified=False,
            diagnostics=["Soft time limit exceeded during symbolic computation"],
        )
        return finding.model_dump()
    except Exception as e:
        finding = FindingResult(
            job_id=bundle.job_id,
            state=FindingState.FAIL,
            diagnostic_code=str(DiagnosticCode.INVALID_AST),
            message=f"Computation encountered unexpected error: {str(e)}",
            dimensions_verified=False,
            diagnostics=[str(e)],
        )
        return finding.model_dump()
