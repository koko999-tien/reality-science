"""Layer 5 Empirical Data Ingestion & Statistical Correlation Engine (Feature 25).

Correlates theoretical AST expressions against structured empirical observations:
- CERN particle collision and resonance data
- NASA cosmological and astrophysical observations
- NIST recommended fundamental physical constants

Strict Zone 3 Security Mandates:
- ZERO eval() / ZERO exec() anywhere in the codebase.
- Safe recursive AST array visitor for vectorized numerical evaluation over NumPy.
- Strict anti-database isolation: worker never accesses databases or networks.
- Pure NumPy, math, and mpmath for statistical distributions (no scipy dependency).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import mpmath
import numpy as np
from pydantic import ConfigDict

from shared.models.enums import DiagnosticCode
from shared.schemas.empirical_data import EmpiricalDatasetSpec
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    VariableSpec,
)
from worker.core.ast_evaluator import (
    MathematicalSingularityError,
    UndeclaredSymbolError,
)


class EmpiricalCorrelationResult(FindingResult):
    """FindingResult extended with Layer 5 empirical correlation metadata."""

    model_config = ConfigDict(extra="allow")

    is_valid: bool = True
    layer: int = 5
    details: Optional[Dict[str, Any]] = None


def extract_ast_symbols(node: ExprNode, symbols: Optional[Set[str]] = None) -> Set[str]:
    """Recursively collects all variable symbol names present in an ExprNode AST."""
    if symbols is None:
        symbols = set()

    if node.node_type == NodeType.VARIABLE and node.value is not None:
        symbols.add(str(node.value))
    elif node.node_type == NodeType.UNARY_OP and node.left is not None:
        extract_ast_symbols(node.left, symbols)
    elif node.node_type == NodeType.BINARY_OP:
        if node.left is not None:
            extract_ast_symbols(node.left, symbols)
        if node.right is not None:
            extract_ast_symbols(node.right, symbols)
    elif node.node_type == NodeType.FUNCTION_CALL and node.args:
        for arg in node.args:
            extract_ast_symbols(arg, symbols)

    return symbols


def safe_evaluate_ast_numerical(
    node: ExprNode,
    env: Dict[str, Union[np.ndarray, float]],
    depth: int = 0,
    max_depth: int = 50,
) -> Union[np.ndarray, float]:
    """Vectorized recursive evaluator for ExprNode AST over NumPy arrays.

    Strictly forbids eval(), exec(), and sympify().
    Recursively computes array results in O(nodes) native speed.
    """
    if depth > max_depth:
        raise ValueError(f"AST recursion depth exceeded maximum limit ({max_depth})")

    if node.node_type == NodeType.CONSTANT:
        if node.value is None:
            raise ValueError("Constant node value cannot be None")
        if isinstance(node.value, (int, float)):
            val = float(node.value)
        elif isinstance(node.value, str):
            val = float(node.value.strip())
        else:
            raise TypeError(f"Unsupported constant type: {type(node.value).__name__}")

        if not math.isfinite(val):
            raise MathematicalSingularityError(f"Non-finite constant in AST: {val}")
        return val

    elif node.node_type == NodeType.VARIABLE:
        if node.value is None:
            raise ValueError("Variable node value cannot be None")
        symbol = str(node.value)
        if symbol in env:
            return env[symbol]
        raise UndeclaredSymbolError(f"Variable '{symbol}' not found in evaluation environment")

    elif node.node_type == NodeType.UNARY_OP:
        if node.left is None:
            raise ValueError("Unary operation requires 'left' operand")
        operand = safe_evaluate_ast_numerical(node.left, env, depth + 1, max_depth)
        if node.op == OperatorType.NEG or node.op == OperatorType.SUB:
            return -operand
        raise ValueError(f"Unsupported unary operator: {node.op}")

    elif node.node_type == NodeType.BINARY_OP:
        if node.left is None or node.right is None:
            raise ValueError("Binary operation requires both 'left' and 'right' operands")
        left_val = safe_evaluate_ast_numerical(node.left, env, depth + 1, max_depth)
        right_val = safe_evaluate_ast_numerical(node.right, env, depth + 1, max_depth)

        if node.op == OperatorType.ADD:
            return left_val + right_val
        elif node.op == OperatorType.SUB:
            return left_val - right_val
        elif node.op == OperatorType.MUL:
            return left_val * right_val
        elif node.op == OperatorType.DIV:
            with np.errstate(divide="ignore", invalid="ignore"):
                result = left_val / right_val
            if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                raise MathematicalSingularityError("Division by zero or singularity in AST model evaluation")
            return result
        elif node.op == OperatorType.POW:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                result = left_val**right_val
            if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                raise MathematicalSingularityError(
                    "Invalid power operation (complex result or overflow singularity)"
                )
            return result
        else:
            raise ValueError(f"Unsupported binary operator: {node.op}")

    elif node.node_type == NodeType.FUNCTION_CALL:
        if not node.args or len(node.args) != 1:
            raise ValueError("Function call requires exactly one argument")
        arg_val = safe_evaluate_ast_numerical(node.args[0], env, depth + 1, max_depth)

        if node.func == AllowedFunction.SQRT:
            if np.any(arg_val < 0.0):
                raise MathematicalSingularityError("Negative radicand in sqrt function")
            return np.sqrt(arg_val)
        elif node.func == AllowedFunction.SIN:
            return np.sin(arg_val)
        elif node.func == AllowedFunction.COS:
            return np.cos(arg_val)
        elif node.func == AllowedFunction.EXP:
            with np.errstate(over="ignore", invalid="ignore"):
                result = np.exp(arg_val)
            if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                raise MathematicalSingularityError("Overflow or singularity in exp function")
            return result
        elif node.func == AllowedFunction.LOG:
            if np.any(arg_val <= 0.0):
                raise MathematicalSingularityError("Non-positive argument in log function")
            return np.log(arg_val)
        else:
            raise ValueError(f"Unsupported function call: {node.func}")

    raise ValueError(f"Unknown node type: {node.node_type}")


def compute_empirical_metrics(
    y_obs: np.ndarray,
    y_theo: np.ndarray,
    sigma: Optional[np.ndarray] = None,
    tolerance_sigma: float = 3.0,
    fitted_parameters_count: int = 0,
    x_coords: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Computes comprehensive statistical metrics between observed data and theoretical predictions.

    Calculates:
    - Residuals: r_i = y_obs,i - y_theo,i
    - Pulls (standardized residuals): z_i = r_i / sigma_i
    - Chi-squared: chi2 = sum(z_i^2)
    - Reduced chi-squared: chi2_red = chi2 / max(1, N - p)
    - Root Mean Square Error (RMSE)
    - Coefficient of Determination (R^2)
    - Chi-squared survival p-value via mpmath incomplete gamma
    - 95% Confidence Interval Coverage
    - Outlier detection beyond tolerance_sigma
    """
    n = len(y_obs)
    if n == 0:
        raise ValueError("Cannot compute metrics on empty dataset")

    residuals = y_obs - y_theo

    # Safe uncertainty handling
    if sigma is None or np.all(sigma <= 0.0):
        # Sample standard error fallback
        sample_std = float(np.std(residuals))
        effective_sigma = np.full(n, max(sample_std, 1e-12))
    else:
        # Guarantee non-zero uncertainties without division by zero
        min_floor = 1e-12 * (np.abs(y_obs) + 1.0)
        effective_sigma = np.where(sigma > 0.0, sigma, min_floor)

    pulls = residuals / effective_sigma
    chi2 = float(np.sum(pulls**2))

    dof = max(1, n - fitted_parameters_count)
    reduced_chi2 = chi2 / dof

    rmse = float(np.sqrt(np.mean(residuals**2)))

    # Coefficient of determination R^2
    y_mean = float(np.mean(y_obs))
    ss_tot = float(np.sum((y_obs - y_mean) ** 2))
    ss_res = float(np.sum(residuals**2))

    if ss_tot < 1e-15:
        r_squared = 1.0 if ss_res < 1e-12 else 0.0
    else:
        r_squared = float(1.0 - (ss_res / ss_tot))

    # P-value calculation using mpmath upper incomplete gamma
    p_value: Optional[float] = None
    if dof > 0 and math.isfinite(chi2) and chi2 >= 0.0:
        try:
            # Regularized upper incomplete gamma Q(a, z) = Gamma(a, z) / Gamma(a)
            p_val_mp = mpmath.gammainc(dof / 2.0, chi2 / 2.0, regularized=True)
            p_value = float(p_val_mp)
        except Exception:
            p_value = None

    # 95% Confidence Interval Bounds & Coverage
    ci_lower = y_theo - 1.96 * effective_sigma
    ci_upper = y_theo + 1.96 * effective_sigma
    within_95 = (y_obs >= ci_lower) & (y_obs <= ci_upper)
    ci_coverage = float(np.mean(within_95))

    # Outlier analysis
    abs_pulls = np.abs(pulls)
    max_residual_sigma = float(np.max(abs_pulls))
    outlier_mask = abs_pulls > tolerance_sigma
    outlier_indices = np.where(outlier_mask)[0]

    outliers = []
    for idx in outlier_indices:
        outlier_entry = {
            "index": int(idx),
            "y_obs": float(y_obs[idx]),
            "y_theo": float(y_theo[idx]),
            "residual": float(residuals[idx]),
            "sigma": float(effective_sigma[idx]),
            "pull_sigma": float(pulls[idx]),
        }
        if x_coords is not None and idx < len(x_coords):
            outlier_entry["x"] = float(x_coords[idx])
        outliers.append(outlier_entry)

    return {
        "sample_size": n,
        "degrees_of_freedom": dof,
        "chi_squared": chi2,
        "reduced_chi_squared": reduced_chi2,
        "rmse": rmse,
        "r_squared": r_squared,
        "p_value": p_value,
        "max_residual_sigma": max_residual_sigma,
        "tolerance_sigma": tolerance_sigma,
        "outlier_count": len(outliers),
        "outliers": outliers,
        "confidence_interval_95": {
            "coverage_fraction": ci_coverage,
            "expected_coverage": 0.95,
            "z_multiplier": 1.96,
        },
        "residuals": [float(r) for r in residuals],
    }


def correlate_empirical_data(
    ast: ExprNode,
    variables: List[VariableSpec],
    dataset: EmpiricalDatasetSpec,
    tolerance_sigma: float = 3.0,
) -> EmpiricalCorrelationResult:
    """Layer 5 Empirical Data Correlation Engine entrypoint.

    Validates AST models against structured CERN, NASA, or NIST empirical observations.
    Evaluates statistical alignment, degrees of freedom, residuals, and tolerance bounds.
    """
    # 1. Dataset existence & data point validation
    x_list, y_list, s_list = dataset.to_xy_sigma()
    if not x_list or not y_list:
        return EmpiricalCorrelationResult(
            job_id="",
            state=FindingState.INSUFFICIENT_DATA,
            diagnostic_code=DiagnosticCode.EMPIRICAL_INSUFFICIENT_DATA.value,
            message=f"Empirical dataset '{dataset.dataset_id}' contains no valid observation points.",
            dimensions_verified=True,
            is_valid=False,
            diagnostics=["Dataset contains 0 observation points."],
        )

    x_arr = np.array(x_list, dtype=np.float64)
    y_obs_arr = np.array(y_list, dtype=np.float64)
    sigma_arr = np.array(s_list, dtype=np.float64)
    n = len(x_arr)

    # 2. Variable mapping and environment construction
    ast_symbols = extract_ast_symbols(ast)
    target_var = dataset.independent_variable_symbol

    # Match AST variable with dataset independent coordinate
    env: Dict[str, Union[np.ndarray, float]] = {}
    if ast_symbols:
        if target_var in ast_symbols:
            env[target_var] = x_arr
        elif len(ast_symbols) == 1:
            matched_sym = next(iter(ast_symbols))
            env[matched_sym] = x_arr
        else:
            # Case-insensitive search
            candidates = [s for s in ast_symbols if s.lower() == target_var.lower()]
            if candidates:
                env[candidates[0]] = x_arr
            else:
                return EmpiricalCorrelationResult(
                    job_id="",
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.UNDECLARED_SYMBOL.value,
                    message=(
                        f"AST variables {list(ast_symbols)} do not match dataset "
                        f"independent coordinate '{target_var}'."
                    ),
                    dimensions_verified=True,
                    is_valid=False,
                    diagnostics=[
                        f"Target independent variable '{target_var}' not declared in model AST {list(ast_symbols)}"
                    ],
                )

    # 3. Model numerical evaluation
    try:
        y_theo_raw = safe_evaluate_ast_numerical(ast, env)
        if np.isscalar(y_theo_raw):
            y_theo_arr = np.full_like(y_obs_arr, float(y_theo_raw))
        else:
            y_theo_arr = np.asarray(y_theo_raw, dtype=np.float64)
    except MathematicalSingularityError as err:
        return EmpiricalCorrelationResult(
            job_id="",
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.SINGULARITY_OR_DIVISION_BY_ZERO.value,
            message=f"Singularity in model evaluation against empirical coordinates: {err}",
            dimensions_verified=True,
            is_valid=False,
            diagnostics=[str(err)],
        )
    except Exception as err:
        return EmpiricalCorrelationResult(
            job_id="",
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.INVALID_AST.value,
            message=f"Evaluation error against empirical data: {err}",
            dimensions_verified=True,
            is_valid=False,
            diagnostics=[str(err)],
        )

    # Check for NaN / Inf in predictions
    if not np.all(np.isfinite(y_theo_arr)):
        return EmpiricalCorrelationResult(
            job_id="",
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.DOMAIN_BOUNDARY_VIOLATION.value,
            message="Theoretical model produced non-finite values (NaN or Inf) at observation coordinates.",
            dimensions_verified=True,
            is_valid=False,
            diagnostics=["Model predictions contain non-finite numbers"],
        )

    # 4. Statistical metrics computation
    metrics = compute_empirical_metrics(
        y_obs=y_obs_arr,
        y_theo=y_theo_arr,
        sigma=sigma_arr,
        tolerance_sigma=tolerance_sigma,
        fitted_parameters_count=0,
        x_coords=x_arr,
    )

    # Attach dataset metadata
    metrics["dataset_id"] = dataset.dataset_id
    metrics["dataset_type"] = dataset.dataset_type.value

    # 5. Statistical decision policy
    outlier_count = metrics["outlier_count"]
    outlier_fraction = outlier_count / n
    max_z = metrics["max_residual_sigma"]
    red_chi2 = metrics["reduced_chi_squared"]

    # Special handling for single NIST reference physical constant (N = 1)
    if n == 1:
        if max_z > tolerance_sigma:
            state = FindingState.FAIL
            diag_code = DiagnosticCode.EMPIRICAL_TOLERANCE_EXCEEDED.value
            msg = (
                f"NIST physical constant deviation ({max_z:.2f} sigma) "
                f"exceeds tolerance ({tolerance_sigma:.1f} sigma)."
            )
            is_valid = False
        elif max_z > 1.0:
            state = FindingState.WARNING
            diag_code = DiagnosticCode.EMPIRICAL_CORRELATION_WARNING.value
            msg = f"NIST physical constant deviation is {max_z:.2f} sigma (within tolerance)."
            is_valid = True
        else:
            state = FindingState.PASS
            diag_code = DiagnosticCode.EMPIRICAL_CORRELATION_PASS.value
            msg = f"NIST physical constant verified within experimental uncertainty ({max_z:.2f} sigma)."
            is_valid = True

    # Standard dataset decision logic (N > 1)
    else:
        # Hard failure conditions:
        # - Reduced chi2 exceeds tolerance^2 (e.g. > 9.0)
        # - Any single data point exceeds 2 * tolerance_sigma (e.g. > 6 sigma)
        # - More than 20% of data points exceed tolerance_sigma
        # - Extremely poor or negative R^2 with significant deviation
        if (
            red_chi2 > (tolerance_sigma**2)
            or max_z > (2.0 * tolerance_sigma)
            or outlier_fraction > 0.20
            or (metrics["r_squared"] < -1.0 and red_chi2 > 4.0)
        ):
            state = FindingState.FAIL
            diag_code = (
                DiagnosticCode.EMPIRICAL_TOLERANCE_EXCEEDED.value
                if outlier_count > 0
                else DiagnosticCode.EMPIRICAL_CORRELATION_FAIL.value
            )
            msg = (
                f"Empirical correlation failed: reduced chi2={red_chi2:.2f}, "
                f"max deviation={max_z:.2f} sigma, {outlier_count} outliers exceeding {tolerance_sigma:.1f} sigma."
            )
            is_valid = False

        # Warning conditions:
        # - Reduced chi2 moderately elevated (2.5 < red_chi2 <= tolerance^2)
        # - Outlier fraction between 5% and 20%
        elif red_chi2 > 3.0 or outlier_fraction > 0.05:
            state = FindingState.WARNING
            diag_code = DiagnosticCode.EMPIRICAL_CORRELATION_WARNING.value
            msg = (
                f"Empirical correlation warning: reduced chi2={red_chi2:.2f}, "
                f"R2={metrics['r_squared']:.4f}, {outlier_count} outliers exceeding {tolerance_sigma:.1f} sigma."
            )
            is_valid = True

        # Pass condition
        else:
            state = FindingState.PASS
            diag_code = DiagnosticCode.EMPIRICAL_CORRELATION_PASS.value
            msg = (
                f"Empirical correlation passed: reduced chi2={red_chi2:.2f}, "
                f"R2={metrics['r_squared']:.4f}, max deviation={max_z:.2f} sigma within {tolerance_sigma:.1f} sigma tolerance."
            )
            is_valid = True

    diagnostics = [
        f"Layer 5 Empirical Correlation: {state.value} ({dataset.dataset_name})",
        f"Sample size: {n}, Reduced Chi2: {red_chi2:.3f}, R2: {metrics['r_squared']:.4f}",
        f"Max standardized deviation: {max_z:.2f} sigma (Tolerance: {tolerance_sigma:.1f} sigma)",
        f"Outliers count: {outlier_count} / {n}",
    ]
    if metrics["p_value"] is not None:
        diagnostics.append(f"Chi2 Survival P-Value: {metrics['p_value']:.4e}")

    return EmpiricalCorrelationResult(
        job_id="",
        state=state,
        diagnostic_code=diag_code,
        message=msg,
        dimensions_verified=True,
        is_valid=is_valid,
        diagnostics=diagnostics,
        details=metrics,
    )
