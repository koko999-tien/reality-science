"""Empirical Observation Data Schemas and Specifications (Feature 25).

Defines Pydantic v2 contracts for CERN particle collision data, NASA astrophysical
observations, NIST fundamental physical constants, and empirical correlation specs.
"""

from __future__ import annotations

from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EmpiricalDatasetType(str, Enum):
    CERN_PARTICLE_COLLISION = "cern_particle_collision"
    NASA_ASTROPHYSICAL = "nasa_astrophysical"
    NIST_PHYSICAL_CONSTANTS = "nist_physical_constants"
    CUSTOM = "custom"
    # Aliases
    CERN = "cern_particle_collision"
    NASA = "nasa_astrophysical"
    NIST = "nist_physical_constants"


# Backward-compatible alias for EmpiricalSourceType
EmpiricalSourceType = EmpiricalDatasetType


class ParticleType(str, Enum):
    MUON_MINUS = "muon-"
    MUON_PLUS = "muon+"
    ELECTRON_MINUS = "electron-"
    ELECTRON_PLUS = "electron+"
    PHOTON = "photon"
    Z_BOSON = "Z0"
    HIGGS_BOSON = "H0"
    W_PLUS = "W+"
    W_MINUS = "W-"
    JET = "jet"
    OTHER = "other"


class EmpiricalDataPoint(BaseModel):
    """Normalized empirical observation data point for statistical correlation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    independent_variable: float = Field(
        default=0.0,
        description="Independent coordinate x (e.g. energy in GeV, redshift z)",
    )
    observed_value: float = Field(
        default=0.0,
        description="Observed dependent value y_obs (e.g. cross section, distance modulus)",
    )
    uncertainty: float = Field(
        default=0.0,
        ge=0.0,
        description="Measurement standard uncertainty sigma >= 0",
    )
    weight: Optional[float] = Field(default=None, ge=0.0, description="Optional weight")
    label: Optional[str] = Field(default=None, description="Observation identifier or label")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extra metadata")

    @model_validator(mode="before")
    @classmethod
    def remap_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Create a shallow copy to modify safely
            data = dict(data)
            # Map 'x' to 'independent_variable' if provided
            if "x" in data:
                val = data.pop("x")
                if "independent_variable" not in data:
                    data["independent_variable"] = val
            # Map 'y_obs' or 'y' to 'observed_value' if provided
            if "y_obs" in data:
                val = data.pop("y_obs")
                if "observed_value" not in data:
                    data["observed_value"] = val
            elif "y" in data:
                val = data.pop("y")
                if "observed_value" not in data:
                    data["observed_value"] = val
            # Map 'sigma' to 'uncertainty' if provided
            if "sigma" in data:
                val = data.pop("sigma")
                if "uncertainty" not in data:
                    data["uncertainty"] = val
        return data

    @property
    def x(self) -> float:
        return self.independent_variable

    @property
    def y_obs(self) -> float:
        return self.observed_value

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty_finite(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise ValueError(f"uncertainty must be a non-negative finite float, got {v}")
        return v

    @field_validator("independent_variable", "observed_value")
    @classmethod
    def validate_finite_coords(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"coordinate value must be a finite float, got {v}")
        return v


class CERNCollisionEvent(BaseModel):
    """CERN LHC particle collision event / particle candidate record."""

    model_config = ConfigDict(extra="forbid")

    event_id: Union[int, str] = Field(..., description="Collision event identifier")
    run_number: int = Field(..., ge=1, description="LHC run number")
    particle_type: str = Field(..., description="Particle candidate identity (e.g. 'muon+', 'electron-', 'Z0', 'H0')")
    pt_gev: float = Field(..., ge=0.0, description="Transverse momentum p_T in GeV")
    eta: float = Field(..., description="Pseudorapidity eta")
    phi: float = Field(..., description="Azimuthal angle phi in radians [-2pi, 2pi]")
    energy_gev: float = Field(..., gt=0.0, description="Total reconstructed energy in GeV")
    invariant_mass_gev: Optional[float] = Field(default=None, ge=0.0, description="Reconstructed invariant mass in GeV")
    uncertainty_gev: Optional[float] = Field(default=None, ge=0.0, description="Measurement uncertainty in GeV")
    charge: Optional[int] = Field(default=None, ge=-2, le=2, description="Particle electric charge in elementary units")
    detector: Optional[str] = Field(default=None, description="Detector name (e.g. 'CMS', 'ATLAS', 'LHCb')")
    luminosity_pb_inv: Optional[float] = Field(default=None, ge=0.0, description="Integrated luminosity in pb^-1")

    @field_validator("phi")
    @classmethod
    def validate_phi(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("phi must be finite")
        if abs(v) > 2 * math.pi + 1e-4:
            raise ValueError(f"phi out of expected angular range [-2pi, 2pi]: {v}")
        return v


class CERNResonanceDataPoint(BaseModel):
    """Binned particle resonance data point (e.g. Z peak or Higgs peak)."""

    model_config = ConfigDict(extra="forbid")

    energy_gev: float = Field(..., gt=0.0, description="Center-of-mass energy or mass bin center in GeV")
    cross_section_pb: Optional[float] = Field(default=None, ge=0.0, description="Measured cross section in picobarns")
    event_count: Optional[int] = Field(default=None, ge=0, description="Observed event count in this bin")
    uncertainty: float = Field(..., ge=0.0, description="Statistical/systematic uncertainty")
    bin_width_gev: Optional[float] = Field(default=None, gt=0.0, description="Bin width in GeV")

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty_finite(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise ValueError(f"uncertainty must be non-negative finite float, got {v}")
        return v


class NASAAstrophysicalObservation(BaseModel):
    """NASA astrophysical observation dataset record (e.g. Type Ia supernovae, Cepheids)."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(..., description="Unique observation or catalog identifier")
    target_name: str = Field(..., description="Target astronomical object name")
    redshift_z: float = Field(..., ge=0.0, description="Cosmological redshift z >= 0")
    distance_modulus_mu: Optional[float] = Field(default=None, description="Distance modulus mu = m - M")
    distance_modulus_error: Optional[float] = Field(default=None, ge=0.0, description="Uncertainty in distance modulus sigma_mu")
    flux_density: Optional[float] = Field(default=None, description="Flux density (e.g. in mJy or W/m^2/Hz)")
    measurement_value: float = Field(..., description="Primary observed quantitative measurement")
    measurement_error: float = Field(..., ge=0.0, description="Standard error / 1-sigma uncertainty of measurement")
    measurement_unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. 'mag', 'km/s', 'mJy')")
    ra_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Right ascension in degrees [0, 360]")
    dec_deg: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Declination in degrees [-90, 90]")
    filter_band: Optional[str] = Field(default=None, description="Photometric optical/IR filter band")
    survey_name: Optional[str] = Field(default=None, description="Observational survey / telescope program")

    @field_validator("measurement_error")
    @classmethod
    def validate_measurement_error_finite(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise ValueError(f"measurement_error must be non-negative finite float, got {v}")
        return v


class NISTPhysicalConstant(BaseModel):
    """NIST CODATA recommended fundamental physical constant reference value."""

    model_config = ConfigDict(extra="forbid")

    constant_symbol: str = Field(..., description="Symbol of constant (e.g. 'c', 'h', 'G', 'e', 'k_B', 'm_e')")
    constant_name: str = Field(..., description="Full descriptive name of constant")
    value: float = Field(..., description="Numerical value of constant in standard SI units")
    standard_uncertainty: float = Field(..., ge=0.0, description="Standard uncertainty (1-sigma). Exactly 0.0 for defining constants.")
    unit: str = Field(..., description="SI unit expression (e.g. 'm / s', 'J * s', 'C')")
    relative_uncertainty: float = Field(default=0.0, ge=0.0, description="Relative standard uncertainty sigma / |value|")
    codata_year: int = Field(default=2022, description="CODATA recommendation edition year")
    is_exact: bool = Field(default=False, description="True if defined exactly under SI 2019 definitions")

    @field_validator("standard_uncertainty")
    @classmethod
    def validate_uncertainty_finite(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise ValueError(f"standard_uncertainty must be non-negative finite float, got {v}")
        return v


class EmpiricalDatasetSpec(BaseModel):
    """Container and specification for empirical datasets ingested into RCE."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(..., description="Unique dataset identifier")
    dataset_name: str = Field(..., description="Human-readable title")
    dataset_type: EmpiricalDatasetType = Field(..., description="Dataset classification")
    source_reference: Optional[str] = Field(default=None, description="Scientific publication citation or DOI")
    description: Optional[str] = Field(default=None, description="Detailed description")
    independent_variable_symbol: str = Field(default="x", description="Symbol of independent variable")
    dependent_variable_symbol: str = Field(default="y", description="Symbol of dependent variable")
    independent_unit: Optional[str] = Field(default=None, description="Unit of independent coordinate (e.g. 'GeV', 'Mpc')")
    dependent_unit: Optional[str] = Field(default=None, description="Unit of dependent observable (e.g. 'picobarn', 'km/s')")
    tolerance_sigma: float = Field(default=3.0, gt=0.0, description="Default statistical tolerance threshold in standard deviations")

    points: List[EmpiricalDataPoint] = Field(default_factory=list, description="Normalized observation points")

    cern_events: Optional[List[CERNCollisionEvent]] = Field(default=None, description="CERN collision event records")
    cern_resonance_points: Optional[List[CERNResonanceDataPoint]] = Field(default=None, description="CERN binned resonance points")
    nasa_observations: Optional[List[NASAAstrophysicalObservation]] = Field(default=None, description="NASA astrophysical observations")
    nist_constants: Optional[List[NISTPhysicalConstant]] = Field(default=None, description="NIST physical constant records")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset metadata")

    @model_validator(mode="before")
    @classmethod
    def remap_dataset_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            # 'name' alias for 'dataset_name'
            if "name" in data:
                val = data.pop("name")
                if "dataset_name" not in data:
                    data["dataset_name"] = val
            # 'source_type' alias for 'dataset_type'
            if "source_type" in data:
                val = data.pop("source_type")
                if "dataset_type" not in data:
                    data["dataset_type"] = val
            # 'source' alias for 'source_reference'
            if "source" in data:
                val = data.pop("source")
                if "source_reference" not in data:
                    data["source_reference"] = val
            # 'independent_variable' alias for 'independent_variable_symbol'
            if "independent_variable" in data:
                val = data.pop("independent_variable")
                if "independent_variable_symbol" not in data:
                    data["independent_variable_symbol"] = val
            # 'dependent_variable' alias for 'dependent_variable_symbol'
            if "dependent_variable" in data:
                val = data.pop("dependent_variable")
                if "dependent_variable_symbol" not in data:
                    data["dependent_variable_symbol"] = val
            # 'data_points' alias for 'points'
            if "data_points" in data:
                val = data.pop("data_points")
                if "points" not in data:
                    data["points"] = val
        return data

    @property
    def data_points(self) -> List[EmpiricalDataPoint]:
        return self.points

    @property
    def independent_variable(self) -> str:
        return self.independent_variable_symbol

    @property
    def dependent_variable(self) -> str:
        return self.dependent_variable_symbol

    def to_xy_sigma(self) -> Tuple[List[float], List[float], List[float]]:
        """Extracts (x_values, y_values, sigma_values) as numerical lists."""
        if self.points:
            x = [p.independent_variable for p in self.points]
            y = [p.observed_value for p in self.points]
            s = [p.uncertainty for p in self.points]
            return x, y, s

        if self.nasa_observations:
            x = [obs.redshift_z for obs in self.nasa_observations]
            y = [
                obs.distance_modulus_mu if obs.distance_modulus_mu is not None else obs.measurement_value
                for obs in self.nasa_observations
            ]
            s = [
                obs.distance_modulus_error if obs.distance_modulus_error is not None else obs.measurement_error
                for obs in self.nasa_observations
            ]
            return x, y, s

        if self.cern_resonance_points:
            x = [p.energy_gev for p in self.cern_resonance_points]
            y = [
                p.cross_section_pb if p.cross_section_pb is not None else float(p.event_count or 0)
                for p in self.cern_resonance_points
            ]
            s = [p.uncertainty for p in self.cern_resonance_points]
            return x, y, s

        if self.cern_events:
            x = [ev.energy_gev for ev in self.cern_events]
            y = [ev.invariant_mass_gev if ev.invariant_mass_gev is not None else ev.pt_gev for ev in self.cern_events]
            s = [ev.uncertainty_gev if ev.uncertainty_gev is not None else 0.1 for ev in self.cern_events]
            return x, y, s

        if self.nist_constants:
            x = [float(i) for i in range(len(self.nist_constants))]
            y = [c.value for c in self.nist_constants]
            s = [c.standard_uncertainty for c in self.nist_constants]
            return x, y, s

        return [], [], []


class EmpiricalFindingDetails(BaseModel):
    """Detailed statistical diagnostic metrics for Layer 5 empirical correlation."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    dataset_type: str
    sample_size: int
    degrees_of_freedom: int
    chi_squared: float
    reduced_chi_squared: float
    rmse: float
    r_squared: float
    max_residual_sigma: float
    tolerance_sigma: float
    outlier_count: int
    outliers: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_interval_95: Dict[str, Any] = Field(default_factory=dict)
    residuals: List[float] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class CorrelationMetrics(BaseModel):
    """Summary statistical correlation metrics for backward compatibility."""

    model_config = ConfigDict(extra="forbid")

    chi_squared: float
    reduced_chi_squared: float
    degrees_of_freedom: int
    rmse: float
    r_squared: float
    max_residual_sigma: float
    tolerance_sigma: float
    confidence_interval_95: Dict[str, float] = Field(default_factory=dict)
    residuals: List[float] = Field(default_factory=list)
    status: str = "COMPUTED"
