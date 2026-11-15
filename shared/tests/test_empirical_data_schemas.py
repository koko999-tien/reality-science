"""Unit tests for Layer 5 Empirical Data Schemas, Diagnostic Codes, and Fixtures."""

import json
import math
import pytest
from pydantic import ValidationError

from shared.models.enums import DiagnosticCode
from shared.schemas.empirical_data import (
    CERNCollisionEvent,
    CERNResonanceDataPoint,
    EmpiricalDataPoint,
    EmpiricalDatasetSpec,
    EmpiricalDatasetType,
    EmpiricalFindingDetails,
    NASAAstrophysicalObservation,
    NISTPhysicalConstant,
    ParticleType,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import ExprNode, NodeType, VariableSpec
from shared.fixtures.empirical.loader import (
    load_cern_higgs_resonance,
    load_cern_z_resonance,
    load_mock_by_name,
    load_nasa_hubble_supernovae,
    load_nist_codata_2022,
)


class TestEmpiricalDataPoint:
    def test_valid_point_creation(self):
        point = EmpiricalDataPoint(
            independent_variable=91.19,
            observed_value=30.5,
            uncertainty=1.2,
            label="Z_peak",
            metadata={"run": 1},
        )
        assert point.independent_variable == 91.19
        assert point.observed_value == 30.5
        assert point.uncertainty == 1.2
        assert point.x == 91.19
        assert point.y_obs == 30.5
        assert point.label == "Z_peak"

    def test_alias_mapping_x_y_sigma(self):
        point = EmpiricalDataPoint.model_validate({
            "x": 125.09,
            "y_obs": 42.0,
            "sigma": 0.5,
            "label": "Higgs",
        })
        assert point.independent_variable == 125.09
        assert point.observed_value == 42.0
        assert point.uncertainty == 0.5

    def test_negative_uncertainty_rejected(self):
        with pytest.raises(ValidationError):
            EmpiricalDataPoint(
                independent_variable=10.0,
                observed_value=20.0,
                uncertainty=-0.5,
            )

    def test_non_finite_coordinate_rejected(self):
        with pytest.raises(ValidationError):
            EmpiricalDataPoint(
                independent_variable=float("nan"),
                observed_value=20.0,
                uncertainty=1.0,
            )

        with pytest.raises(ValidationError):
            EmpiricalDataPoint(
                independent_variable=10.0,
                observed_value=float("inf"),
                uncertainty=1.0,
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            EmpiricalDataPoint.model_validate({
                "independent_variable": 1.0,
                "observed_value": 2.0,
                "uncertainty": 0.1,
                "unauthorized_field": "injected",
            })


class TestCERNCollisionEvent:
    def test_valid_event(self):
        event = CERNCollisionEvent(
            event_id=101,
            run_number=12345,
            particle_type="Z0",
            pt_gev=45.0,
            eta=0.5,
            phi=1.2,
            energy_gev=91.2,
            invariant_mass_gev=91.1876,
            uncertainty_gev=0.08,
            detector="CMS",
        )
        assert event.event_id == 101
        assert event.particle_type == "Z0"
        assert event.energy_gev == 91.2

    def test_phi_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            CERNCollisionEvent(
                event_id=102,
                run_number=12345,
                particle_type="muon+",
                pt_gev=40.0,
                eta=0.0,
                phi=10.0,  # > 2*pi
                energy_gev=50.0,
            )


class TestNASAAstrophysicalObservation:
    def test_valid_observation(self):
        obs = NASAAstrophysicalObservation(
            observation_id="NASA-HST-SN1994D",
            target_name="SN 1994D",
            redshift_z=0.0055,
            distance_modulus_mu=31.89,
            distance_modulus_error=0.15,
            measurement_value=31.89,
            measurement_error=0.15,
            measurement_unit="mag",
            filter_band="B",
        )
        assert obs.redshift_z == 0.0055
        assert obs.distance_modulus_mu == 31.89
        assert obs.measurement_error == 0.15

    def test_negative_error_rejected(self):
        with pytest.raises(ValidationError):
            NASAAstrophysicalObservation(
                observation_id="OBS-1",
                target_name="Galaxy",
                redshift_z=0.1,
                measurement_value=20.0,
                measurement_error=-0.5,
            )


class TestNISTPhysicalConstant:
    def test_exact_constant(self):
        c = NISTPhysicalConstant(
            constant_symbol="c",
            constant_name="speed of light in vacuum",
            value=299792458.0,
            standard_uncertainty=0.0,
            unit="m / s",
            is_exact=True,
        )
        assert c.value == 299792458.0
        assert c.standard_uncertainty == 0.0
        assert c.is_exact is True

    def test_measured_constant(self):
        g = NISTPhysicalConstant(
            constant_symbol="G",
            constant_name="gravitational constant",
            value=6.67430e-11,
            standard_uncertainty=1.5e-15,
            unit="m^3 / (kg * s^2)",
            relative_uncertainty=2.2e-5,
            is_exact=False,
        )
        assert g.value == 6.67430e-11
        assert g.standard_uncertainty > 0.0


class TestEmpiricalDatasetSpec:
    def test_to_xy_sigma_from_points(self):
        spec = EmpiricalDatasetSpec(
            dataset_id="test-ds-1",
            dataset_name="Test Points Dataset",
            dataset_type=EmpiricalDatasetType.CUSTOM,
            independent_variable_symbol="x",
            dependent_variable_symbol="y",
            points=[
                EmpiricalDataPoint(independent_variable=1.0, observed_value=2.0, uncertainty=0.1),
                EmpiricalDataPoint(independent_variable=2.0, observed_value=4.0, uncertainty=0.2),
                EmpiricalDataPoint(independent_variable=3.0, observed_value=6.0, uncertainty=0.3),
            ],
        )
        x, y, s = spec.to_xy_sigma()
        assert x == [1.0, 2.0, 3.0]
        assert y == [2.0, 4.0, 6.0]
        assert s == [0.1, 0.2, 0.3]

    def test_alias_support(self):
        raw = {
            "dataset_id": "test-alias",
            "name": "Alias Test",
            "source_type": "custom",
            "independent_variable": "energy",
            "dependent_variable": "flux",
            "data_points": [
                {"x": 10.0, "y_obs": 100.0, "sigma": 5.0},
            ],
        }
        spec = EmpiricalDatasetSpec.model_validate(raw)
        assert spec.dataset_name == "Alias Test"
        assert spec.dataset_type == EmpiricalDatasetType.CUSTOM
        assert spec.independent_variable_symbol == "energy"
        assert spec.dependent_variable_symbol == "flux"
        assert len(spec.points) == 1
        assert spec.points[0].independent_variable == 10.0


class TestJobBundleAndFindingResultExtensions:
    def test_job_bundle_with_empirical_dataset(self):
        ds = EmpiricalDatasetSpec(
            dataset_id="bundle-ds",
            dataset_name="Bundle Dataset",
            dataset_type=EmpiricalDatasetType.CUSTOM,
            points=[EmpiricalDataPoint(independent_variable=1.0, observed_value=2.0, uncertainty=0.1)],
        )
        bundle = JobBundle(
            job_id="job-emp-1",
            version_id="ver-1",
            target_entity_type=TargetEntityType.EQUATION,
            target_entity_id="eq-1",
            expression_ast=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
            variables=[VariableSpec(name="x", symbol="x", unit="dimensionless")],
            units=[],
            empirical_dataset=ds,
            empirical_tolerance_sigma=2.5,
        )
        assert bundle.empirical_dataset is not None
        assert bundle.empirical_dataset.dataset_id == "bundle-ds"
        assert bundle.empirical_tolerance_sigma == 2.5

    def test_job_bundle_without_empirical_dataset_backwards_compatible(self):
        bundle = JobBundle(
            job_id="job-classic-1",
            version_id="ver-1",
            target_entity_type=TargetEntityType.EQUATION,
            target_entity_id="eq-1",
            expression_ast=ExprNode(node_type=NodeType.CONSTANT, value=1.0),
            variables=[],
            units=[],
        )
        assert bundle.empirical_dataset is None
        assert bundle.empirical_tolerance_sigma == 3.0

    def test_finding_result_details_and_layer(self):
        res = FindingResult(
            job_id="res-1",
            state=FindingState.PASS,
            diagnostic_code=DiagnosticCode.EMPIRICAL_CORRELATION_PASS.value,
            message="Correlation passed",
            dimensions_verified=True,
            layer=5,
            details={"chi_squared": 1.25, "reduced_chi_squared": 1.05, "r_squared": 0.99},
        )
        assert res.layer == 5
        assert res.details is not None
        assert res.details["chi_squared"] == 1.25


class TestLayer5DiagnosticCodes:
    def test_diagnostic_codes_defined(self):
        assert DiagnosticCode.EMPIRICAL_CORRELATION_PASS.value == "EMPIRICAL_CORRELATION_PASS"
        assert DiagnosticCode.EMPIRICAL_CORRELATION_FAIL.value == "EMPIRICAL_CORRELATION_FAIL"
        assert DiagnosticCode.EMPIRICAL_TOLERANCE_EXCEEDED.value == "EMPIRICAL_TOLERANCE_EXCEEDED"
        assert DiagnosticCode.EMPIRICAL_INSUFFICIENT_DATA.value == "EMPIRICAL_INSUFFICIENT_DATA"
        assert DiagnosticCode.EMPIRICAL_NOT_APPLICABLE.value == "EMPIRICAL_NOT_APPLICABLE"
        assert DiagnosticCode.EMPIRICAL_CORRELATION_WARNING.value == "EMPIRICAL_CORRELATION_WARNING"
        assert DiagnosticCode.EMPIRICAL_SCHEMA_INVALID.value == "EMPIRICAL_SCHEMA_INVALID"
        assert DiagnosticCode.EMPIRICAL_UNIT_MISMATCH.value == "EMPIRICAL_UNIT_MISMATCH"


class TestMockDatasetFixtures:
    def test_load_cern_z_resonance(self):
        ds = load_cern_z_resonance()
        assert ds.dataset_id == "cern-lhc-z-resonance-peak"
        assert len(ds.points) == 13
        x, y, s = ds.to_xy_sigma()
        assert min(x) == 86.0
        assert max(x) == 96.0
        assert max(y) > 25.0  # Peak is around 30.5 nb
        assert ds.cern_events is not None
        assert len(ds.cern_events) == 3

    def test_load_cern_higgs_resonance(self):
        ds = load_cern_higgs_resonance()
        assert ds.dataset_id == "cern-lhc-higgs-boson-peak"
        assert len(ds.points) == 13
        x, y, s = ds.to_xy_sigma()
        assert min(x) == 116.0
        assert max(x) == 134.0
        assert ds.cern_events is not None

    def test_load_nasa_hubble_supernovae(self):
        ds = load_nasa_hubble_supernovae()
        assert ds.dataset_id == "nasa-hst-type-ia-supernovae"
        assert len(ds.points) == 13
        x, y, s = ds.to_xy_sigma()
        assert min(x) < 0.01
        assert max(x) > 1.0
        assert min(y) > 30.0
        assert ds.nasa_observations is not None

    def test_load_nist_codata_2022(self):
        ds = load_nist_codata_2022()
        assert ds.dataset_id == "nist-codata-2022-fundamental-constants"
        assert len(ds.points) == 13
        assert ds.nist_constants is not None
        # Check c
        c_item = next(c for c in ds.nist_constants if c.constant_symbol == "c")
        assert c_item.value == 299792458.0
        assert c_item.is_exact is True

    def test_load_mock_by_name(self):
        ds_z = load_mock_by_name("cern_z")
        assert ds_z.dataset_id == "cern-lhc-z-resonance-peak"
        ds_h = load_mock_by_name("cern_higgs")
        assert ds_h.dataset_id == "cern-lhc-higgs-boson-peak"
        ds_nasa = load_mock_by_name("nasa_hubble")
        assert ds_nasa.dataset_id == "nasa-hst-type-ia-supernovae"
        ds_nist = load_mock_by_name("nist_codata")
        assert ds_nist.dataset_id == "nist-codata-2022-fundamental-constants"

    def test_load_mock_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_mock_by_name("non_existent_universe")
