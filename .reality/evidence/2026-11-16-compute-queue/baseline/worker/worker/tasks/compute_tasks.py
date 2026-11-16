from typing import Dict, List, Optional
from celery.exceptions import SoftTimeLimitExceeded
from worker.celery_app import celery_app
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.finding_result import FindingResult, FindingState, LayerFinding
from shared.models.enums import DiagnosticCode
from worker.core.semantic_validator import validate_ast_semantics
from worker.core.complexity_guard import inspect_ast_complexity
from worker.core.boundary_engine import analyze_boundary_and_singularities
from worker.tasks.dimensional import execute_dimensional_verification
from worker.core.physical_invariants import verify_physical_invariants
from worker.core.empirical_engine import correlate_empirical_data
from worker.core.epistemic_engine import verify_claim_graph

LAYER_NAMES = {
    1: "Syntax & Semantics",
    2: "Boundary & Singularities",
    3: "Dimensional Analysis",
    4: "Physical Laws & Invariants",
    5: "Empirical Correlation",
    6: "Epistemic Logic",
}


@celery_app.task(name="worker.tasks.verify_equation_ast", bind=True)
def verify_equation_ast(self, bundle_data: dict) -> dict:
    """Executes the full 6-layer Reality Constraint Engine (RCE) validation pipeline:
    - Layer 1: Syntax & Semantics
    - Layer 2: Boundary & Singularities
    - Layer 3: Dimensional Analysis (Pint 100+ units)
    - Layer 4: Physical Laws & Invariants (c bound, energy & momentum conservation)
    - Layer 5: Empirical Observation Correlation (CERN/NASA/NIST fitting)
    - Layer 6: Epistemic Logic (cross-claim graph, cyclic dependencies, contradiction)
    """
    bundle = JobBundle.model_validate(bundle_data)
    layer_findings: Dict[int, LayerFinding] = {}

    try:
        # Branch A: Pure Claim Graph verification
        if bundle.claim_graph is not None and (bundle.expression_ast is None or bundle.target_entity_type == TargetEntityType.CLAIM):
            l6_res = verify_claim_graph(bundle.claim_graph)
            if l6_res.cycle_report.cycle_detected:
                diag_code = DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value
                msg = f"Circular dependency detected in claim graph: {len(l6_res.cycle_report.cycles)} cycle(s)."
            elif l6_res.contradiction_report.contradictions_found:
                diag_code = DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value
                msg = f"Cross-claim contradiction detected in claim graph: {len(l6_res.contradiction_report.items)} conflict(s)."
            elif l6_res.overall_state == FindingState.FAIL:
                diag_code = DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value
                msg = "Antecedent failure poisoned dependent claims."
            elif l6_res.overall_state == FindingState.WARNING:
                diag_code = DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value
                msg = "Epistemic graph verified with antecedent warning(s)."
            elif l6_res.overall_state in (FindingState.INSUFFICIENT_DATA, FindingState.NOT_YET_TESTED):
                diag_code = DiagnosticCode.EPISTEMIC_DEPENDENCY_UNRESOLVED.value
                msg = "Epistemic graph has unresolved antecedent dependencies."
            else:
                diag_code = DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
                msg = "Epistemic logic graph successfully verified with zero cycles and zero contradictions."

            for l in range(1, 6):
                layer_findings[l] = LayerFinding(
                    layer=l,
                    name=f"Layer {l}: {LAYER_NAMES[l]}",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code="NOT_APPLICABLE_CLAIM_ENTITY",
                    message=f"Layer {l} skipped: Target entity is pure claim graph.",
                    diagnostics=[],
                )

            layer_findings[6] = LayerFinding(
                layer=6,
                name=f"Layer 6: {LAYER_NAMES[6]}",
                state=l6_res.overall_state,
                diagnostic_code=diag_code,
                message=msg,
                diagnostics=l6_res.diagnostics,
                details=l6_res.model_dump(),
            )

            finding = FindingResult(
                job_id=bundle.job_id,
                state=l6_res.overall_state,
                diagnostic_code=diag_code,
                message=msg,
                dimensions_verified=True,
                diagnostics=l6_res.diagnostics,
                details=l6_res.model_dump(),
                layer=6,
                layer_findings=layer_findings,
            )
            return finding.model_dump()

        # Layer 1: Definition, Complexity, & Semantic Checks
        l1_res = validate_ast_semantics(bundle.expression_ast, bundle.variables, bundle.units)
        if not l1_res.is_valid:
            layer_findings[1] = LayerFinding(
                layer=1,
                name=f"Layer 1: {LAYER_NAMES[1]}",
                state=FindingState.FAIL,
                diagnostic_code=l1_res.diagnostic_code,
                message=l1_res.message,
                diagnostics=l1_res.diagnostics,
                details={"referenced_symbols": list(l1_res.referenced_symbols)},
            )
            for l in range(2, 7):
                layer_findings[l] = LayerFinding(
                    layer=l,
                    name=f"Layer {l}: {LAYER_NAMES[l]}",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code="SKIPPED_GATE",
                    message=f"Layer {l} skipped due to Layer 1 failure.",
                    diagnostics=[],
                )

            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=l1_res.diagnostic_code,
                message=l1_res.message,
                dimensions_verified=False,
                diagnostics=l1_res.diagnostics,
                layer=1,
                layer_findings=layer_findings,
            )
            return finding.model_dump()

        # Layer 1 Passed
        node_count, max_depth = inspect_ast_complexity(bundle.expression_ast) if bundle.expression_ast else (0, 0)
        layer_findings[1] = LayerFinding(
            layer=1,
            name=f"Layer 1: {LAYER_NAMES[1]}",
            state=FindingState.PASS,
            diagnostic_code="VALIDATION_PASSED",
            message=f"Syntax and semantic checks passed ({len(l1_res.referenced_symbols)} symbols, {node_count} nodes, depth {max_depth}).",
            diagnostics=[f"Referenced symbols: {sorted(list(l1_res.referenced_symbols))}"],
            details={"node_count": node_count, "max_depth": max_depth, "referenced_symbols": list(l1_res.referenced_symbols)},
        )

        # Layer 2: Boundary & Singularity Solver + Symbolic Consistency
        l2_res = analyze_boundary_and_singularities(bundle.expression_ast, bundle.variables)
        if not l2_res.is_valid:
            layer_findings[2] = LayerFinding(
                layer=2,
                name=f"Layer 2: {LAYER_NAMES[2]}",
                state=l2_res.state,
                diagnostic_code=l2_res.diagnostic_code,
                message=l2_res.message,
                diagnostics=l2_res.diagnostics,
                details={"simplified_expr": l2_res.simplified_expr},
            )
            for l in range(3, 7):
                layer_findings[l] = LayerFinding(
                    layer=l,
                    name=f"Layer {l}: {LAYER_NAMES[l]}",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code="SKIPPED_GATE",
                    message=f"Layer {l} skipped due to Layer 2 boundary/singularity failure.",
                    diagnostics=[],
                )

            finding = FindingResult(
                job_id=bundle.job_id,
                state=l2_res.state,
                diagnostic_code=l2_res.diagnostic_code,
                message=l2_res.message,
                dimensions_verified=False,
                diagnostics=l2_res.diagnostics,
                layer=2,
                layer_findings=layer_findings,
            )
            return finding.model_dump()

        # Layer 2 Passed or Warning
        layer_findings[2] = LayerFinding(
            layer=2,
            name=f"Layer 2: {LAYER_NAMES[2]}",
            state=l2_res.state,
            diagnostic_code=l2_res.diagnostic_code,
            message=l2_res.message,
            diagnostics=l2_res.diagnostics,
            details={"simplified_expr": l2_res.simplified_expr},
        )

        # Layer 3: Dimensional SI Homogeneity & Transcendental Checks
        dim_ok, dim_str, dim_diag = execute_dimensional_verification(
            bundle.expression_ast, bundle.variables, bundle.units
        )
        if not dim_ok:
            layer_findings[3] = LayerFinding(
                layer=3,
                name=f"Layer 3: {LAYER_NAMES[3]}",
                state=FindingState.FAIL,
                diagnostic_code=dim_diag,
                message=f"Dimensional consistency check failed: {dim_diag}",
                diagnostics=[f"Dimensional verification failure: {dim_diag}"],
                details={"inferred_dimension": dim_str},
            )
            for l in range(4, 7):
                layer_findings[l] = LayerFinding(
                    layer=l,
                    name=f"Layer {l}: {LAYER_NAMES[l]}",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code="SKIPPED_GATE",
                    message=f"Layer {l} skipped due to Layer 3 dimensional failure.",
                    diagnostics=[],
                )

            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.FAIL,
                diagnostic_code=dim_diag,
                message=f"Dimensional consistency check failed: {dim_diag}",
                dimensions_verified=False,
                diagnostics=[f"Dimensional verification failure: {dim_diag}"],
                layer=3,
                layer_findings=layer_findings,
            )
            return finding.model_dump()

        # Layer 3 Passed
        layer_findings[3] = LayerFinding(
            layer=3,
            name=f"Layer 3: {LAYER_NAMES[3]}",
            state=FindingState.PASS,
            diagnostic_code="VALIDATION_PASSED",
            message=f"Dimensional consistency verified: {dim_str}",
            diagnostics=[f"Inferred dimension: {dim_str}"],
            details={"inferred_dimension": dim_str},
        )

        # Layer 4: Physical Laws Invariants (v <= c, Delta E = 0, Delta P = 0)
        l4_res = None
        if bundle.system_context is not None:
            l4_res = verify_physical_invariants(
                bundle.expression_ast, bundle.variables, bundle.system_context
            )
            layer_findings[4] = LayerFinding(
                layer=4,
                name=f"Layer 4: {LAYER_NAMES[4]}",
                state=l4_res.state,
                diagnostic_code=l4_res.diagnostic_code,
                message=l4_res.message,
                diagnostics=l4_res.diagnostics,
                details=getattr(l4_res, "details", None),
            )
            if not l4_res.is_valid:
                for l in range(5, 7):
                    layer_findings[l] = LayerFinding(
                        layer=l,
                        name=f"Layer {l}: {LAYER_NAMES[l]}",
                        state=FindingState.NOT_APPLICABLE,
                        diagnostic_code="SKIPPED_GATE",
                        message=f"Layer {l} skipped due to Layer 4 physical invariant failure.",
                        diagnostics=[],
                    )

                diagnostics = [
                    f"Layer 1 Syntax: OK ({len(l1_res.referenced_symbols)} symbols)",
                    f"Layer 2 Boundary: OK ({l2_res.simplified_expr})",
                    f"Layer 3 Dimension: OK ({dim_str})",
                    *l2_res.diagnostics,
                    *l4_res.diagnostics,
                ]
                finding = FindingResult(
                    job_id=bundle.job_id,
                    state=l4_res.state,
                    diagnostic_code=l4_res.diagnostic_code,
                    message=l4_res.message,
                    symbolic_simplification=l2_res.simplified_expr,
                    dimensions_verified=True,
                    diagnostics=diagnostics,
                    layer=4,
                    layer_findings=layer_findings,
                )
                return finding.model_dump()
        else:
            layer_findings[4] = LayerFinding(
                layer=4,
                name=f"Layer 4: {LAYER_NAMES[4]}",
                state=FindingState.NOT_APPLICABLE,
                diagnostic_code="NO_SYSTEM_CONTEXT",
                message="No physical system context declared for invariant checks.",
                diagnostics=[],
            )

        # Layer 5: Empirical Observation Data Correlation
        l5_res = None
        if bundle.empirical_dataset is not None:
            l5_res = correlate_empirical_data(
                ast=bundle.expression_ast,
                variables=bundle.variables,
                dataset=bundle.empirical_dataset,
                tolerance_sigma=bundle.empirical_tolerance_sigma,
            )
            layer_findings[5] = LayerFinding(
                layer=5,
                name=f"Layer 5: {LAYER_NAMES[5]}",
                state=l5_res.state,
                diagnostic_code=l5_res.diagnostic_code,
                message=l5_res.message,
                diagnostics=l5_res.diagnostics,
                details=l5_res.details,
            )
            if not l5_res.is_valid:
                layer_findings[6] = LayerFinding(
                    layer=6,
                    name=f"Layer 6: {LAYER_NAMES[6]}",
                    state=FindingState.NOT_APPLICABLE,
                    diagnostic_code="SKIPPED_GATE",
                    message="Layer 6 skipped due to Layer 5 empirical correlation failure.",
                    diagnostics=[],
                )
                diagnostics = [
                    f"Layer 1 Syntax: OK ({len(l1_res.referenced_symbols)} symbols)",
                    f"Layer 2 Boundary: OK ({l2_res.simplified_expr})",
                    f"Layer 3 Dimension: OK ({dim_str})",
                    *l2_res.diagnostics,
                    *(l4_res.diagnostics if l4_res is not None else []),
                    *l5_res.diagnostics,
                ]
                finding = FindingResult(
                    job_id=bundle.job_id,
                    state=l5_res.state,
                    diagnostic_code=l5_res.diagnostic_code,
                    message=l5_res.message,
                    symbolic_simplification=l2_res.simplified_expr,
                    dimensions_verified=True,
                    diagnostics=diagnostics,
                    details=l5_res.details,
                    layer=5,
                    layer_findings=layer_findings,
                )
                return finding.model_dump()
        else:
            layer_findings[5] = LayerFinding(
                layer=5,
                name=f"Layer 5: {LAYER_NAMES[5]}",
                state=FindingState.NOT_APPLICABLE,
                diagnostic_code="NO_EMPIRICAL_DATA",
                message="No empirical observation dataset attached.",
                diagnostics=[],
            )

        # Layer 6: Epistemic Logic Verification (if claim_graph provided)
        l6_res = None
        if bundle.claim_graph is not None:
            l6_res = verify_claim_graph(bundle.claim_graph)
            diag_code_6 = (
                DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value
                if l6_res.cycle_report.cycle_detected
                else (
                    DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value
                    if l6_res.contradiction_report.contradictions_found
                    else (
                        DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value
                        if l6_res.overall_state == FindingState.FAIL
                        else (
                            DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value
                            if l6_res.overall_state == FindingState.WARNING
                            else DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
                        )
                    )
                )
            )
            layer_findings[6] = LayerFinding(
                layer=6,
                name=f"Layer 6: {LAYER_NAMES[6]}",
                state=l6_res.overall_state,
                diagnostic_code=diag_code_6,
                message=(
                    "Epistemic logic verification failed for attached claim graph."
                    if l6_res.overall_state == FindingState.FAIL
                    else "Epistemic logic graph evaluated."
                ),
                diagnostics=l6_res.diagnostics,
                details=l6_res.model_dump(),
            )
            if l6_res.overall_state == FindingState.FAIL:
                diagnostics = [
                    f"Layer 1 Syntax: OK ({len(l1_res.referenced_symbols)} symbols)",
                    f"Layer 2 Boundary: OK ({l2_res.simplified_expr})",
                    f"Layer 3 Dimension: OK ({dim_str})",
                    *l2_res.diagnostics,
                    *(l4_res.diagnostics if l4_res is not None else []),
                    *(l5_res.diagnostics if l5_res is not None else []),
                    *l6_res.diagnostics,
                ]
                finding = FindingResult(
                    job_id=bundle.job_id,
                    state=FindingState.FAIL,
                    diagnostic_code=diag_code_6,
                    message="Epistemic logic verification failed for attached claim graph.",
                    symbolic_simplification=l2_res.simplified_expr,
                    dimensions_verified=True,
                    diagnostics=diagnostics,
                    details=l6_res.model_dump(),
                    layer=6,
                    layer_findings=layer_findings,
                )
                return finding.model_dump()
        else:
            layer_findings[6] = LayerFinding(
                layer=6,
                name=f"Layer 6: {LAYER_NAMES[6]}",
                state=FindingState.NOT_APPLICABLE,
                diagnostic_code="NO_CLAIM_GRAPH",
                message="No epistemic claim graph declared.",
                diagnostics=[],
            )

        # Composite diagnostics assembly
        diagnostics = [
            f"Layer 1 Syntax: OK ({len(l1_res.referenced_symbols)} symbols)",
            f"Layer 2 Boundary: OK ({l2_res.simplified_expr})",
            f"Layer 3 Dimension: OK ({dim_str})",
            *l2_res.diagnostics,
        ]
        if l4_res is not None:
            diagnostics.extend(l4_res.diagnostics)
        if l5_res is not None:
            diagnostics.extend(l5_res.diagnostics)
        if l6_res is not None:
            diagnostics.extend(l6_res.diagnostics)

        # Determine composite finding state and diagnostic code using canonical severity ordering
        if l6_res is not None and l6_res.overall_state == FindingState.WARNING:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.WARNING,
                diagnostic_code=DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value,
                message="Epistemic graph verified with antecedent warning(s).",
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
                details=l6_res.model_dump(),
                layer=6,
                layer_findings=layer_findings,
            )
        elif l5_res is not None and l5_res.state == FindingState.WARNING:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.WARNING,
                diagnostic_code=l5_res.diagnostic_code,
                message=l5_res.message,
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
                details=l5_res.details,
                layer=5,
                layer_findings=layer_findings,
            )
        elif (l4_res is not None and l4_res.state == FindingState.WARNING) or l2_res.state == FindingState.WARNING:
            warn_state = l4_res.state if (l4_res is not None and l4_res.state == FindingState.WARNING) else l2_res.state
            warn_code = l4_res.diagnostic_code if (l4_res is not None and l4_res.state == FindingState.WARNING) else l2_res.diagnostic_code
            warn_msg = l4_res.message if (l4_res is not None and l4_res.state == FindingState.WARNING) else l2_res.message
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.WARNING,
                diagnostic_code=warn_code,
                message=warn_msg,
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
                details=l5_res.details if l5_res is not None else getattr(l4_res, "details", None),
                layer=5 if l5_res is not None else (4 if l4_res is not None else 2),
                layer_findings=layer_findings,
            )
        elif l4_res is not None and l4_res.state == FindingState.NOT_APPLICABLE and l5_res is None and bundle.system_context is not None:
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.NOT_APPLICABLE,
                diagnostic_code=l4_res.diagnostic_code,
                message=l4_res.message,
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
                layer=4,
                layer_findings=layer_findings,
            )
        else:
            msg = (
                "Mathematical AST passed semantic, boundary, dimensional, physical invariant, and empirical correlation checks."
                if l5_res is not None
                else (
                    "Mathematical AST passed all 6 reality constraint validation layers."
                    if l6_res is not None
                    else (
                        "Mathematical AST passed semantic, boundary/singularity, dimensional, and physical invariant checks."
                        if l4_res is not None
                        else "Mathematical AST passed semantic, boundary/singularity, and dimensional consistency checks."
                    )
                )
            )
            finding = FindingResult(
                job_id=bundle.job_id,
                state=FindingState.PASS,
                diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
                message=msg,
                symbolic_simplification=l2_res.simplified_expr,
                dimensions_verified=True,
                diagnostics=diagnostics,
                details=l5_res.details if l5_res is not None else (getattr(l4_res, "details", None) if l4_res is not None else None),
                layer=5 if l5_res is not None else (4 if l4_res is not None else 3),
                layer_findings=layer_findings,
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
            layer_findings=layer_findings or None,
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
            layer_findings=layer_findings or None,
        )
        return finding.model_dump()
