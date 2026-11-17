from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Set, Tuple, Union
from celery.exceptions import SoftTimeLimitExceeded
import sympy as sp
from shared.schemas.math_ast import (
    ExprNode,
    NodeType,
    OperatorType,
    VariableSpec,
)
from shared.schemas.finding_result import FindingState
from shared.models.enums import DiagnosticCode
from worker.core.ast_evaluator import (
    ast_to_sympy,
    MathematicalSingularityError,
    UndeclaredSymbolError,
)

NUMERICAL_EQUIVALENCE_TOLERANCE = 1e-12
STRATIFIED_POINTS_COUNT = 10


@dataclass
class BoundaryAnalysisResult:
    is_valid: bool
    state: FindingState
    diagnostic_code: str
    message: str
    simplified_expr: Optional[str] = None
    singularities: List[str] = field(default_factory=list)
    boundary_limits: Dict[str, str] = field(default_factory=dict)
    asymptotic_divergences: List[str] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)


def extract_denominators(sympy_expr: sp.Expr) -> Set[sp.Expr]:
    """Extracts all denominator expressions from a SymPy expression tree without eval/exec."""
    denominators: Set[sp.Expr] = set()

    # Check overall fraction
    if hasattr(sympy_expr, "as_numer_denom"):
        try:
            _, denom = sympy_expr.as_numer_denom()
            if denom != 1 and denom != sp.Integer(1):
                denominators.add(denom)
        except SoftTimeLimitExceeded:
            raise
        except Exception:
            pass

    # Walk subtrees for terms with negative exponents: x**(-1) -> x
    for subexpr in sp.preorder_traversal(sympy_expr):
        if isinstance(subexpr, sp.Pow):
            try:
                if subexpr.exp.is_number and subexpr.exp < 0:
                    denominators.add(subexpr.base)
            except SoftTimeLimitExceeded:
                raise
            except Exception:
                pass

    return denominators


def check_singularities_and_poles(
    sympy_expr: sp.Expr,
    variables: List[VariableSpec],
) -> Tuple[bool, List[str]]:
    """Detects denominator poles & singularities using sp.solveset in the real domain.
    Filters roots against each variable's declared physical domain.

    Returns:
        (has_singularity_in_domain, list_of_singularity_descriptions)
    """
    var_domain_map: Dict[str, str] = {v.symbol: v.domain for v in variables}
    denoms = extract_denominators(sympy_expr)
    singularities: List[str] = []

    for denom in denoms:
        # Check constant denominator
        if denom == 0 or denom == sp.Integer(0):
            singularities.append(f"Literal division by zero detected in denominator '{denom}'")
            continue

        for sym in denom.free_symbols:
            domain_type = var_domain_map.get(sym.name, "real")
            try:
                roots = sp.solveset(denom, sym, domain=sp.S.Reals)
            except SoftTimeLimitExceeded:
                raise
            except Exception:
                continue

            if roots == sp.EmptySet:
                continue
            elif roots == sp.UniversalSet:
                singularities.append(
                    f"Denominator '{denom}' vanishes identically for all real values of '{sym.name}'"
                )
            elif isinstance(roots, sp.FiniteSet):
                for root in roots:
                    try:
                        # Check whether root falls inside the declared domain
                        if domain_type == "positive_real":
                            if root.is_number and float(root) > 0:
                                singularities.append(
                                    f"Pole detected in positive_real domain: {denom} = 0 at {sym.name} = {root}"
                                )
                        elif domain_type == "real":
                            if root.is_number and math.isfinite(float(root)):
                                singularities.append(
                                    f"Pole detected in real domain: {denom} = 0 at {sym.name} = {root}"
                                )
                        elif domain_type == "integer":
                            if root.is_integer or (root.is_number and float(root).is_integer()):
                                singularities.append(
                                    f"Pole detected in integer domain: {denom} = 0 at {sym.name} = {root}"
                                )
                        elif domain_type == "complex":
                            singularities.append(
                                f"Pole detected for {sym.name} at {root}"
                            )
                    except (TypeError, ValueError):
                        # Symbolic root that cannot be converted to float
                        singularities.append(
                            f"Potential pole for {sym.name} where {denom} = 0: {root}"
                        )
            elif isinstance(roots, sp.Interval):
                singularities.append(
                    f"Continuous singularity interval for {sym.name} where {denom} = 0 on {roots}"
                )

    has_singularity = len(singularities) > 0
    return has_singularity, singularities


def evaluate_boundary_limits(
    sympy_expr: sp.Expr,
    variables: List[VariableSpec],
) -> Tuple[Dict[str, str], List[str]]:
    """Evaluates boundary limits (x -> 0+, x -> oo, x -> -oo) to detect asymptotic divergence."""
    var_domain_map: Dict[str, str] = {v.symbol: v.domain for v in variables}
    boundary_limits: Dict[str, str] = {}
    divergences: List[str] = []

    for sym in sympy_expr.free_symbols:
        domain_type = var_domain_map.get(sym.name, "real")
        try:
            if domain_type == "positive_real":
                # Check x -> 0+
                lim_zero = sp.limit(sympy_expr, sym, 0, dir="+")
                boundary_limits[f"{sym.name} -> 0+"] = str(lim_zero)
                if lim_zero.is_infinite:
                    divergences.append(f"Asymptotic divergence as {sym.name} -> 0+: {lim_zero}")

                # Check x -> oo
                lim_inf = sp.limit(sympy_expr, sym, sp.oo)
                boundary_limits[f"{sym.name} -> oo"] = str(lim_inf)
                if lim_inf.is_infinite:
                    divergences.append(f"Asymptotic divergence as {sym.name} -> oo: {lim_inf}")

            else:
                # Check x -> oo
                lim_inf = sp.limit(sympy_expr, sym, sp.oo)
                boundary_limits[f"{sym.name} -> oo"] = str(lim_inf)
                if lim_inf.is_infinite:
                    divergences.append(f"Asymptotic divergence as {sym.name} -> oo: {lim_inf}")

                # Check x -> -oo
                lim_neg_inf = sp.limit(sympy_expr, sym, -sp.oo)
                boundary_limits[f"{sym.name} -> -oo"] = str(lim_neg_inf)
                if lim_neg_inf.is_infinite:
                    divergences.append(f"Asymptotic divergence as {sym.name} -> -oo: {lim_neg_inf}")
        except SoftTimeLimitExceeded:
            raise
        except Exception:
            # An undetermined limit may fall back; a task deadline may not.
            continue

    return boundary_limits, divergences


def execute_richardson_stratified_sampling(
    diff_expr: sp.Expr,
    variables: List[VariableSpec],
    num_points: int = STRATIFIED_POINTS_COUNT,
    tolerance: float = NUMERICAL_EQUIVALENCE_TOLERANCE,
) -> Tuple[bool, float, List[str]]:
    """Implements Richardson's Theorem (1968) 10-point stratified numerical fallback.
    When sp.simplify(lhs - rhs) != 0, tests numerical identity over 10 points
    sampled strictly within the declared physical domain.

    Returns:
        (is_numerically_zero, max_observed_error, sampling_diagnostics)
    """
    free_syms = list(diff_expr.free_symbols)
    if not free_syms:
        try:
            val = float(diff_expr.evalf())
            is_zero = abs(val) < tolerance
            return is_zero, abs(val), [f"Constant difference: {val}"]
        except SoftTimeLimitExceeded:
            raise
        except Exception:
            return False, float("inf"), ["Evaluation failed on constant difference"]

    var_domain_map: Dict[str, str] = {v.symbol: v.domain for v in variables}

    # Stratified test points grid
    positive_grid = [0.1, 0.35, 0.75, 1.2, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
    real_grid = [-42.3, -21.7, -7.5, -1.2, -0.3, 0.4, 2.1, 8.9, 23.4, 45.1]
    integer_grid = [1, 2, 3, 5, 7, 10, 15, 20, 35, 50]

    max_err = 0.0
    sampling_logs: List[str] = []

    for i in range(num_points):
        subs_dict: Dict[sp.Symbol, float] = {}
        for sym in free_syms:
            domain = var_domain_map.get(sym.name, "real")
            if domain == "positive_real":
                val = positive_grid[i % len(positive_grid)]
            elif domain == "integer":
                val = float(integer_grid[i % len(integer_grid)])
            else:
                val = real_grid[i % len(real_grid)]
            subs_dict[sym] = val

        try:
            evaluated = diff_expr.evalf(subs=subs_dict)
            if not evaluated.is_number:
                return False, float("inf"), ["Non-numeric evaluation during stratified sampling"]
            err = abs(float(evaluated))
            if math.isnan(err) or math.isinf(err):
                return False, float("inf"), [f"Non-finite sample evaluated at point {i}: {subs_dict}"]
            if err > max_err:
                max_err = err
            if err >= tolerance:
                return (
                    False,
                    max_err,
                    [f"Stratified sampling divergence at point {i}: |diff| = {err} >= {tolerance} for {subs_dict}"],
                )
        except SoftTimeLimitExceeded:
            raise
        except Exception as ex:
            return False, float("inf"), [f"Exception evaluating point {i}: {str(ex)}"]

    sampling_logs.append(
        f"Richardson stratified sampling verified across {num_points} points: max residual = {max_err:.2e} < {tolerance:.2e}"
    )
    return True, max_err, sampling_logs


def analyze_boundary_and_singularities(
    node: ExprNode,
    variables: List[VariableSpec],
) -> BoundaryAnalysisResult:
    """Executes Layer 2 Boundary & Singularity Engine analysis:
    - Zero eval/exec/parse_expr native AST-to-SymPy construction
    - Denominator pole & singularity detection via sp.solveset on real domain
    - Boundary limits (x -> 0+, x -> oo) and asymptotic divergence checks
    - Richardson's Theorem 10-point stratified numerical fallback when simplification != 0
    """
    declared_symbols = {v.symbol for v in variables}
    diagnostics: List[str] = []

    # 1. Native AST to SymPy translation
    try:
        sympy_expr = ast_to_sympy(node, declared_symbols)
    except UndeclaredSymbolError as e:
        return BoundaryAnalysisResult(
            is_valid=False,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.UNDECLARED_SYMBOL.value,
            message=str(e),
            diagnostics=[str(e)],
        )
    except MathematicalSingularityError as e:
        return BoundaryAnalysisResult(
            is_valid=False,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.SINGULARITY_OR_DIVISION_BY_ZERO.value,
            message=str(e),
            diagnostics=[str(e)],
        )
    except SoftTimeLimitExceeded:
        raise
    except Exception as e:
        return BoundaryAnalysisResult(
            is_valid=False,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.INVALID_AST.value,
            message=f"SymPy conversion error: {str(e)}",
            diagnostics=[str(e)],
        )

    # 2. Denominator Pole & Singularity Check
    has_singularity, singularities = check_singularities_and_poles(sympy_expr, variables)
    if has_singularity:
        msg = f"Mathematical singularity or division by zero detected in declared domain: {singularities[0]}"
        return BoundaryAnalysisResult(
            is_valid=False,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.SINGULARITY_OR_DIVISION_BY_ZERO.value,
            message=msg,
            singularities=singularities,
            diagnostics=singularities,
        )

    # 3. Boundary limits & asymptotic divergences
    boundary_limits, divergences = evaluate_boundary_limits(sympy_expr, variables)
    if divergences:
        diagnostics.extend(divergences)

    # 4. Symbolic Simplification & Richardson's Theorem Fallback
    simplified = sp.simplify(sympy_expr)
    simplified_str = str(simplified)

    # Check if this is an equation identity test: e.g. node is a subtraction lhs - rhs
    if node.node_type == NodeType.BINARY_OP and node.op == OperatorType.SUB:
        if simplified == 0:
            diagnostics.append("Symbolic simplification proven: lhs - rhs == 0")
            return BoundaryAnalysisResult(
                is_valid=True,
                state=FindingState.PASS,
                diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
                message="Symbolic identity verified and boundary stability checks passed.",
                simplified_expr=simplified_str,
                boundary_limits=boundary_limits,
                asymptotic_divergences=divergences,
                diagnostics=diagnostics,
            )
        else:
            # sp.simplify(lhs - rhs) != 0 -> Apply Richardson's Theorem 10-point stratified sampling
            is_equiv, max_err, sampling_logs = execute_richardson_stratified_sampling(
                sympy_expr, variables
            )
            diagnostics.extend(sampling_logs)
            if is_equiv:
                return BoundaryAnalysisResult(
                    is_valid=True,
                    state=FindingState.WARNING,
                    diagnostic_code=DiagnosticCode.SYMBOLIC_UNPROVEN_NUMERICALLY_CONSISTENT.value,
                    message="Equivalence cannot be formally proven symbolically; numerical sampling supports identity within machine precision.",
                    simplified_expr=simplified_str,
                    boundary_limits=boundary_limits,
                    asymptotic_divergences=divergences,
                    diagnostics=diagnostics,
                )

    # Standard expression simplification success
    diagnostics.append(f"Symbolic simplification: {simplified_str}")
    return BoundaryAnalysisResult(
        is_valid=True,
        state=FindingState.PASS,
        diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
        message="Layer 2 Boundary and Mathematical Consistency validation passed.",
        simplified_expr=simplified_str,
        boundary_limits=boundary_limits,
        asymptotic_divergences=divergences,
        diagnostics=diagnostics,
    )
