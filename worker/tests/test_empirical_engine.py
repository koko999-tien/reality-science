"""Unit tests for Layer 5 Empirical Data Correlation Engine (Feature 25)."""

import math
import numpy as np
import pytest

from shared.fixtures.empirical.loader import (
    load_cern_higgs_resonance,
    load_cern_z_resonance,
    load_nasa_hubble_supernovae,
    load_nist_codata_2022,
)
from shared.models.enums import DiagnosticCode
from shared.schemas.empirical_data import (
    EmpiricalDataPoint,
    EmpiricalDatasetSpec,
    EmpiricalDatasetType,
    NISTPhysicalConstant,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)
from worker.core.ast_evaluator import (
    MathematicalSingularityError,
    UndeclaredSymbolError,
)
from worker.core.empirical_engine import (
    compute_empirical_metrics,
    correlate_empirical_data,
    extract_ast_symbols,
    safe_evaluate_ast_numerical,
)
from worker.tasks.compute_tasks import verify_equation_ast


class TestVectorizedASTEvaluator:
    def test_safe_evaluate_ast_numerical_basic_math(self):
        # f(x) = (x + 2.0) * 3.0 - 1.0 / 2.0
        # Build AST: ((x + 2) * 3) - (1 / 2)
        node = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.SUB,
            left=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.MUL,
                left=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.ADD,
                    left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                ),
                right=ExprNode(node_type=NodeType.CONSTANT, value=3.0),
            ),
            right=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.DIV,
                left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
                right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
            ),
        )
        x_vals = np.array([1.0, 2.0, 3.0, 4.0])
        env = {"x": x_vals}
        result = safe_evaluate_ast_numerical(node, env)
        expected = (x_vals + 2.0) * 3.0 - 0.5
        np.testing.assert_allclose(result, expected)

    def test_safe_evaluate_ast_functions(self):
        # Test sqrt(x)
        sqrt_node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.SQRT,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        )
        x_vals = np.array([1.0, 4.0, 9.0, 16.0])
        np.testing.assert_allclose(safe_evaluate_ast_numerical(sqrt_node, {"x": x_vals}), [1.0, 2.0, 3.0, 4.0])

        # Test exp(x) and log(x)
        exp_node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.EXP,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        )
        log_node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.LOG,
            args=[exp_node],
        )
        x_linear = np.array([0.5, 1.0, 2.0, 3.0])
        np.testing.assert_allclose(safe_evaluate_ast_numerical(log_node, {"x": x_linear}), x_linear)

    def test_singularities_caught(self):
        # Division by zero: 1.0 / x at x = 0.0
        div_node = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.DIV,
            left=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
            right=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        )
        with pytest.raises(MathematicalSingularityError):
            safe_evaluate_ast_numerical(div_node, {"x": np.array([1.0, 0.0, 2.0])})

        # Sqrt of negative number
        sqrt_node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=AllowedFunction.SQRT,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        )
        with pytest.raises(MathematicalSingularityError):
            safe_evaluate_ast_numerical(sqrt_node, {"x": np.array([4.0, -1.0])})

    def test_undeclared_symbol_error(self):
        node = ExprNode(node_type=NodeType.VARIABLE, value="undeclared_var")
        with pytest.raises(UndeclaredSymbolError):
            safe_evaluate_ast_numerical(node, {"x": np.array([1.0, 2.0])})


class TestEmpiricalMetricsComputation:
    def test_perfect_fit_metrics(self):
        y_obs = np.array([10.0, 20.0, 30.0, 40.0])
        y_theo = np.array([10.0, 20.0, 30.0, 40.0])
        sigma = np.array([1.0, 1.0, 1.0, 1.0])

        metrics = compute_empirical_metrics(y_obs, y_theo, sigma=sigma, tolerance_sigma=3.0)
        assert metrics["sample_size"] == 4
        assert metrics["chi_squared"] == 0.0
        assert metrics["reduced_chi_squared"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["r_squared"] == 1.0
        assert metrics["outlier_count"] == 0
        assert metrics["confidence_interval_95"]["coverage_fraction"] == 1.0
        assert metrics["p_value"] == 1.0

    def test_statistical_deviation_and_outliers(self):
        y_obs = np.array([10.0, 20.0, 30.0, 40.0])
        # Point 3 deviates by 4 sigma (uncertainty is 1.0, diff is 4.0)
        y_theo = np.array([10.0, 20.0, 34.0, 40.0])
        sigma = np.array([1.0, 1.0, 1.0, 1.0])

        metrics = compute_empirical_metrics(y_obs, y_theo, sigma=sigma, tolerance_sigma=3.0)
        assert metrics["outlier_count"] == 1
        assert metrics["outliers"][0]["index"] == 2
        assert metrics["max_residual_sigma"] == 4.0
        assert metrics["chi_squared"] == 16.0
        assert metrics["reduced_chi_squared"] == 4.0


class TestCERNBreitWignerFit:
    def test_cern_z_resonance_peak_fit_pass(self):
        # Breit-Wigner formula centered at M_Z = 91.1876, Gamma_Z = 2.4952, sigma_0 = 30.5 nb
        mz = 91.1876
        gamma_z = 2.4952
        sigma_0 = 30.5
        gamma_sq = gamma_z**2
        mz_sq = mz**2

        c1 = sigma_0 * gamma_sq
        c2 = gamma_sq / mz_sq

        # AST: (c1 * (E ** 2)) / (((E ** 2) - mz_sq) ** 2 + c2 * (E ** 4))
        ast = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.DIV,
            left=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.MUL,
                left=ExprNode(node_type=NodeType.CONSTANT, value=c1),
                right=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.POW,
                    left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                ),
            ),
            right=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.ADD,
                left=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.POW,
                    left=ExprNode(
                        node_type=NodeType.BINARY_OP,
                        op=OperatorType.SUB,
                        left=ExprNode(
                            node_type=NodeType.BINARY_OP,
                            op=OperatorType.POW,
                            left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                            right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                        ),
                        right=ExprNode(node_type=NodeType.CONSTANT, value=mz_sq),
                    ),
                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                ),
                right=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.MUL,
                    left=ExprNode(node_type=NodeType.CONSTANT, value=c2),
                    right=ExprNode(
                        node_type=NodeType.BINARY_OP,
                        op=OperatorType.POW,
                        left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                        right=ExprNode(node_type=NodeType.CONSTANT, value=4.0),
                    ),
                ),
            ),
        )

        dataset = load_cern_z_resonance()
        result = correlate_empirical_data(
            ast=ast,
            variables=[VariableSpec(name="E", symbol="E", unit="dimensionless")],
            dataset=dataset,
            tolerance_sigma=3.0,
        )

        assert result.is_valid is True
        assert result.state == FindingState.PASS
        assert result.diagnostic_code == DiagnosticCode.EMPIRICAL_CORRELATION_PASS.value
        assert result.details is not None
        assert result.details["r_squared"] > 0.99
        assert result.details["reduced_chi_squared"] < 1.0

    def test_cern_z_resonance_shifted_peak_fail(self):
        # A flat constant model f(E) = 1.0 nb strongly disagrees with the Z peak (30.5 nb)
        flat_ast = ExprNode(node_type=NodeType.CONSTANT, value=1.0)
        dataset = load_cern_z_resonance()

        result = correlate_empirical_data(
            ast=flat_ast,
            variables=[VariableSpec(name="E", symbol="E", unit="dimensionless")],
            dataset=dataset,
            tolerance_sigma=3.0,
        )

        assert result.is_valid is False
        assert result.state == FindingState.FAIL
        assert result.diagnostic_code in (
            DiagnosticCode.EMPIRICAL_TOLERANCE_EXCEEDED.value,
            DiagnosticCode.EMPIRICAL_CORRELATION_FAIL.value,
        )
        assert result.details["outlier_count"] > 0


class TestNASAHubbleFit:
    def test_nasa_hubble_supernovae_correlation_pass(self):
        # Standard Lambda-CDM expansion: mu(z) ~ 43.16 + 2.17147 * ln(z + 0.3 * z^2)
        # AST: 43.16 + 2.17147 * log(z + 0.3 * (z ** 2))
        ast = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.ADD,
            left=ExprNode(node_type=NodeType.CONSTANT, value=43.16),
            right=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.MUL,
                left=ExprNode(node_type=NodeType.CONSTANT, value=2.17147),
                right=ExprNode(
                    node_type=NodeType.FUNCTION_CALL,
                    func=AllowedFunction.LOG,
                    args=[
                        ExprNode(
                            node_type=NodeType.BINARY_OP,
                            op=OperatorType.ADD,
                            left=ExprNode(node_type=NodeType.VARIABLE, value="z"),
                            right=ExprNode(
                                node_type=NodeType.BINARY_OP,
                                op=OperatorType.MUL,
                                left=ExprNode(node_type=NodeType.CONSTANT, value=0.3),
                                right=ExprNode(
                                    node_type=NodeType.BINARY_OP,
                                    op=OperatorType.POW,
                                    left=ExprNode(node_type=NodeType.VARIABLE, value="z"),
                                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                                ),
                            ),
                        )
                    ],
                ),
            ),
        )

        dataset = load_nasa_hubble_supernovae()
        result = correlate_empirical_data(
            ast=ast,
            variables=[VariableSpec(name="z", symbol="z", unit="dimensionless")],
            dataset=dataset,
            tolerance_sigma=3.0,
        )

        assert result.is_valid is True
        assert result.state == FindingState.PASS
        assert result.details is not None
        assert result.details["r_squared"] > 0.99
        assert result.details["reduced_chi_squared"] < 2.0
        assert result.details["outlier_count"] == 0

    def test_nasa_hubble_unphysical_negative_slope_fail(self):
        # Unphysical model: mu(z) = -100.0 * z
        unphysical_ast = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.CONSTANT, value=-100.0),
            right=ExprNode(node_type=NodeType.VARIABLE, value="z"),
        )
        dataset = load_nasa_hubble_supernovae()
        result = correlate_empirical_data(
            ast=unphysical_ast,
            variables=[VariableSpec(name="z", symbol="z", unit="dimensionless")],
            dataset=dataset,
            tolerance_sigma=3.0,
        )
        assert result.is_valid is False
        assert result.state == FindingState.FAIL


class TestNISTPhysicalConstants:
    def test_nist_constant_verification_pass(self):
        # Model for speed of light: c = 299792458.0
        ast_c = ExprNode(node_type=NodeType.CONSTANT, value=299792458.0)
        c_point = NISTPhysicalConstant(
            constant_symbol="c",
            constant_name="speed of light",
            value=299792458.0,
            standard_uncertainty=0.0,
            unit="m / s",
            is_exact=True,
        )
        dataset = EmpiricalDatasetSpec(
            dataset_id="nist-c-test",
            dataset_name="NIST Speed of Light Test",
            dataset_type=EmpiricalDatasetType.NIST_PHYSICAL_CONSTANTS,
            points=[
                EmpiricalDataPoint(
                    independent_variable=0.0,
                    observed_value=299792458.0,
                    uncertainty=0.0,
                    label="c",
                )
            ],
            nist_constants=[c_point],
        )

        result = correlate_empirical_data(
            ast=ast_c,
            variables=[],
            dataset=dataset,
            tolerance_sigma=3.0,
        )
        assert result.is_valid is True
        assert result.state == FindingState.PASS

    def test_nist_constant_deviation_tolerance_exceeded(self):
        # Gravitational constant G = 6.67430e-11 with standard uncertainty 1.5e-15
        # Propose unphysical G = 6.67430e-11 + 10 * 1.5e-15 (10-sigma deviation)
        true_g = 6.67430e-11
        unc_g = 1.5e-15
        erroneous_g = true_g + 10.0 * unc_g

        ast_g = ExprNode(node_type=NodeType.CONSTANT, value=erroneous_g)
        dataset = EmpiricalDatasetSpec(
            dataset_id="nist-g-test",
            dataset_name="NIST Gravitational Constant Test",
            dataset_type=EmpiricalDatasetType.NIST_PHYSICAL_CONSTANTS,
            points=[
                EmpiricalDataPoint(
                    independent_variable=0.0,
                    observed_value=true_g,
                    uncertainty=unc_g,
                    label="G",
                )
            ],
        )

        result = correlate_empirical_data(
            ast=ast_g,
            variables=[],
            dataset=dataset,
            tolerance_sigma=3.0,
        )
        assert result.is_valid is False
        assert result.state == FindingState.FAIL
        assert result.diagnostic_code == DiagnosticCode.EMPIRICAL_TOLERANCE_EXCEEDED.value


class TestPipelineIntegration:
    def test_pipeline_with_empirical_dataset(self):
        # Build JobBundle with empirical CERN Z resonance dataset
        mz, gamma_z, sigma_0 = 91.1876, 2.4952, 30.5
        c1 = sigma_0 * (gamma_z**2)
        c2 = (gamma_z**2) / (mz**2)
        mz_sq = mz**2

        ast = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.DIV,
            left=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.MUL,
                left=ExprNode(node_type=NodeType.CONSTANT, value=c1),
                right=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.POW,
                    left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                ),
            ),
            right=ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.ADD,
                left=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.POW,
                    left=ExprNode(
                        node_type=NodeType.BINARY_OP,
                        op=OperatorType.SUB,
                        left=ExprNode(
                            node_type=NodeType.BINARY_OP,
                            op=OperatorType.POW,
                            left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                            right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                        ),
                        right=ExprNode(node_type=NodeType.CONSTANT, value=mz_sq),
                    ),
                    right=ExprNode(node_type=NodeType.CONSTANT, value=2.0),
                ),
                right=ExprNode(
                    node_type=NodeType.BINARY_OP,
                    op=OperatorType.MUL,
                    left=ExprNode(node_type=NodeType.CONSTANT, value=c2),
                    right=ExprNode(
                        node_type=NodeType.BINARY_OP,
                        op=OperatorType.POW,
                        left=ExprNode(node_type=NodeType.VARIABLE, value="E"),
                        right=ExprNode(node_type=NodeType.CONSTANT, value=4.0),
                    ),
                ),
            ),
        )

        dataset = load_cern_z_resonance()
        bundle = JobBundle(
            job_id="job-cern-z-pipe",
            version_id="ver-1",
            target_entity_type=TargetEntityType.EQUATION,
            target_entity_id="eq-z",
            expression_ast=ast,
            variables=[VariableSpec(name="E", symbol="E", unit="dimensionless")],
            units=[],
            empirical_dataset=dataset,
            empirical_tolerance_sigma=3.0,
        )

        res_dict = verify_equation_ast(bundle.model_dump())
        res = FindingResult.model_validate(res_dict)
        assert res.state == FindingState.PASS
        assert res.layer == 5
        assert res.details is not None
        assert res.details["reduced_chi_squared"] < 1.0
        assert any("Layer 5 Empirical Correlation: PASS" in d for d in res.diagnostics)

    def test_pipeline_clean_skip_when_no_empirical_dataset(self):
        var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
        var_t = VariableSpec(symbol="t", name="time", unit="second")
        # v * t -> [length]
        node = ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.MUL,
            left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
            right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
        )
        bundle = JobBundle(
            job_id="job-no-emp",
            version_id="ver-1",
            target_entity_type=TargetEntityType.EQUATION,
            target_entity_id="eq-1",
            expression_ast=node,
            variables=[var_v, var_t],
            units=[],
            empirical_dataset=None,
        )
        res_dict = verify_equation_ast(bundle.model_dump())
        res = FindingResult.model_validate(res_dict)
        assert res.state == FindingState.PASS
        assert not any("Layer 5" in d for d in res.diagnostics)
