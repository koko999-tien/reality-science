"""Empirical Dataset Loaders and Fixture Utilities (Milestone 2).

Provides cached loader functions for CERN, NASA, and NIST reference datasets.
"""

from __future__ import annotations

import csv
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Dict, List

from shared.schemas.empirical_data import (
    CERNCollisionEvent,
    CERNResonanceDataPoint,
    EmpiricalDataPoint,
    EmpiricalDatasetSpec,
    EmpiricalDatasetType,
    NASAAstrophysicalObservation,
    NISTPhysicalConstant,
)

FIXTURES_DIR = Path("D:/Reality_Science/shared/fixtures/empirical")


def ensure_fixtures_exist() -> None:
    """Generates the reference JSON and CSV mock files if they do not yet exist."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. CERN Z0 Resonance
    z_json = FIXTURES_DIR / "cern_z_resonance.json"
    z_csv = FIXTURES_DIR / "cern_z_resonance.csv"
    if not z_json.exists():
        mz, gamma_z, sigma_peak = 91.1876, 2.4952, 30.5
        energies = [86.0, 88.0, 89.0, 90.0, 90.5, 91.0, 91.19, 91.5, 92.0, 92.5, 93.0, 94.0, 96.0]
        z_points, z_res_points = [], []
        for e in energies:
            s = e * e
            num = sigma_peak * (s * gamma_z * gamma_z)
            denom = (s - mz * mz) ** 2 + (s * s * gamma_z * gamma_z / (mz * mz))
            cs = num / denom
            err = max(0.25, cs * 0.04)
            z_points.append(
                EmpiricalDataPoint(
                    independent_variable=round(e, 4),
                    observed_value=round(cs, 4),
                    uncertainty=round(err, 4),
                    label=f"Z0_E_{e:.2f}GeV",
                    metadata={"energy_gev": e, "unit": "nb"},
                )
            )
            z_res_points.append(
                CERNResonanceDataPoint(
                    energy_gev=round(e, 4),
                    cross_section_pb=round(cs * 1000, 2),
                    uncertainty=round(err * 1000, 2),
                    bin_width_gev=0.5,
                )
            )
        z_events = [
            CERNCollisionEvent(
                event_id=10001,
                run_number=300001,
                particle_type="Z0",
                pt_gev=44.2,
                eta=0.12,
                phi=1.15,
                energy_gev=91.18,
                invariant_mass_gev=91.1876,
                uncertainty_gev=0.08,
                charge=0,
                detector="CMS",
                luminosity_pb_inv=45.2,
            ),
            CERNCollisionEvent(
                event_id=10002,
                run_number=300001,
                particle_type="muon+",
                pt_gev=45.6,
                eta=-0.45,
                phi=-2.10,
                energy_gev=49.8,
                invariant_mass_gev=0.10566,
                uncertainty_gev=0.01,
                charge=1,
                detector="CMS",
            ),
            CERNCollisionEvent(
                event_id=10003,
                run_number=300001,
                particle_type="muon-",
                pt_gev=45.5,
                eta=0.48,
                phi=1.04,
                energy_gev=50.2,
                invariant_mass_gev=0.10566,
                uncertainty_gev=0.01,
                charge=-1,
                detector="CMS",
            ),
        ]
        z_spec = EmpiricalDatasetSpec(
            dataset_id="cern-lhc-z-resonance-peak",
            dataset_name="CERN LHC Z0 Boson Invariant Mass & Resonance Distribution",
            dataset_type=EmpiricalDatasetType.CERN_PARTICLE_COLLISION,
            source_reference="CERN-EP-2022-045 / Phys.Rev.D 105 (2022)",
            description="Cross-section resonance scan and dimuon invariant mass distribution for Z0 boson (M_Z = 91.1876 GeV)",
            independent_variable_symbol="E",
            dependent_variable_symbol="cross_section",
            tolerance_sigma=3.0,
            points=z_points,
            cern_events=z_events,
            cern_resonance_points=z_res_points,
            metadata={"lhc_center_of_mass_energy_tev": 13.0, "decay_channel": "Z -> mu+ mu-"},
        )
        with open(z_json, "w", encoding="utf-8") as f:
            json.dump(z_spec.model_dump(), f, indent=2)

        with open(z_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["independent_variable", "observed_value", "uncertainty", "label"])
            for p in z_points:
                writer.writerow([p.independent_variable, p.observed_value, p.uncertainty, p.label])

    # 2. CERN Higgs Resonance
    h_json = FIXTURES_DIR / "cern_higgs_resonance.json"
    h_csv = FIXTURES_DIR / "cern_higgs_resonance.csv"
    if not h_json.exists():
        mh, sigma_exp = 125.09, 1.8
        masses = [116.0, 118.0, 120.0, 122.0, 123.5, 124.5, 125.09, 125.5, 126.5, 128.0, 130.0, 132.0, 134.0]
        h_points, h_res_points = [], []
        for m in masses:
            bg = 150.0 * math.exp(-0.02 * (m - 110.0))
            sig = 35.0 * math.exp(-0.5 * ((m - mh) / sigma_exp) ** 2)
            tot = bg + sig
            err = math.sqrt(tot)
            h_points.append(
                EmpiricalDataPoint(
                    independent_variable=round(m, 4),
                    observed_value=round(tot, 2),
                    uncertainty=round(err, 2),
                    label=f"H0_m_{m:.2f}GeV",
                    metadata={"invariant_mass_gev": m, "signal_contribution": round(sig, 2)},
                )
            )
            h_res_points.append(
                CERNResonanceDataPoint(
                    energy_gev=round(m, 4),
                    event_count=int(round(tot)),
                    uncertainty=round(err, 2),
                    bin_width_gev=1.0,
                )
            )
        h_events = [
            CERNCollisionEvent(
                event_id=20001,
                run_number=310020,
                particle_type="H0",
                pt_gev=65.2,
                eta=0.08,
                phi=0.85,
                energy_gev=125.1,
                invariant_mass_gev=125.09,
                uncertainty_gev=0.24,
                charge=0,
                detector="ATLAS",
                luminosity_pb_inv=139000.0,
            ),
            CERNCollisionEvent(
                event_id=20002,
                run_number=310020,
                particle_type="photon",
                pt_gev=62.8,
                eta=0.15,
                phi=0.82,
                energy_gev=63.5,
                invariant_mass_gev=0.0,
                uncertainty_gev=0.15,
                detector="ATLAS",
            ),
        ]
        h_spec = EmpiricalDatasetSpec(
            dataset_id="cern-lhc-higgs-boson-peak",
            dataset_name="CERN LHC Higgs Boson Invariant Mass Distribution (H -> gamma gamma)",
            dataset_type=EmpiricalDatasetType.CERN_PARTICLE_COLLISION,
            source_reference="ATLAS & CMS Collaborations / Phys.Rev.Lett. 114 (2015) 191803",
            description="Higgs boson invariant mass resonance distribution centered at 125.09 GeV in diphoton decay channel",
            independent_variable_symbol="m",
            dependent_variable_symbol="event_count",
            tolerance_sigma=3.0,
            points=h_points,
            cern_events=h_events,
            cern_resonance_points=h_res_points,
            metadata={"lhc_center_of_mass_energy_tev": 13.0, "decay_channel": "H -> gamma gamma"},
        )
        with open(h_json, "w", encoding="utf-8") as f:
            json.dump(h_spec.model_dump(), f, indent=2)

        with open(h_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["independent_variable", "observed_value", "uncertainty", "label"])
            for p in h_points:
                writer.writerow([p.independent_variable, p.observed_value, p.uncertainty, p.label])

    # 3. NASA Hubble Supernovae
    nasa_json = FIXTURES_DIR / "nasa_hubble_supernovae.json"
    nasa_csv = FIXTURES_DIR / "nasa_hubble_supernovae.csv"
    if not nasa_json.exists():
        sn_catalog = [
            ("SN 1994D", 0.0055, 31.89, 0.15, 187.2, 13.2, "B"),
            ("SN 1998bw", 0.0085, 32.85, 0.16, 293.7, -18.8, "V"),
            ("SN 1990N", 0.0140, 33.93, 0.14, 190.1, 15.5, "B"),
            ("SN 1992A", 0.0260, 35.30, 0.15, 189.5, -28.5, "B"),
            ("SN 1999ee", 0.0520, 36.84, 0.16, 21.3, -36.2, "V"),
            ("SN 1997ce", 0.1200, 38.76, 0.18, 142.5, 35.2, "V"),
            ("SN 1996E", 0.2400, 40.42, 0.19, 110.8, -12.1, "R"),
            ("SN 1995K", 0.4800, 42.18, 0.21, 54.3, -25.8, "R"),
            ("SN 1997cj", 0.5000, 42.29, 0.22, 178.2, 0.5, "R"),
            ("SN 1998ba", 0.6200, 42.86, 0.23, 195.4, 2.1, "I"),
            ("SN 1997ff", 0.8500, 43.69, 0.25, 189.1, 62.2, "F814W"),
            ("SN 2002dc", 1.0500, 44.26, 0.27, 215.3, 15.8, "F814W"),
            ("SN 2003es", 1.2500, 44.73, 0.30, 160.7, 41.2, "F814W"),
        ]
        nasa_obs, nasa_points = [], []
        for name, z, mu, sig, ra, dec, band in sn_catalog:
            clean_name = name.replace(" ", "-")
            nasa_obs.append(
                NASAAstrophysicalObservation(
                    observation_id=f"NASA-HST-{clean_name}",
                    target_name=name,
                    redshift_z=z,
                    distance_modulus_mu=mu,
                    distance_modulus_error=sig,
                    measurement_value=mu,
                    measurement_error=sig,
                    measurement_unit="mag",
                    ra_deg=ra,
                    dec_deg=dec,
                    filter_band=band,
                    survey_name="Hubble Space Telescope Supernova Survey / Pantheon+",
                )
            )
            nasa_points.append(
                EmpiricalDataPoint(
                    independent_variable=z,
                    observed_value=mu,
                    uncertainty=sig,
                    label=name,
                    metadata={"filter_band": band, "ra_deg": ra, "dec_deg": dec},
                )
            )
        nasa_spec = EmpiricalDatasetSpec(
            dataset_id="nasa-hst-type-ia-supernovae",
            dataset_name="NASA Hubble Space Telescope Type Ia Supernova Redshift vs Distance Modulus",
            dataset_type=EmpiricalDatasetType.NASA_ASTROPHYSICAL,
            source_reference="Riess et al. / Astrophys.J. 826 (2016) & Scolnic et al. Pantheon+ (2022)",
            description="Cosmological redshift-distance modulus observations of Type Ia standard candles",
            independent_variable_symbol="z",
            dependent_variable_symbol="mu",
            tolerance_sigma=3.0,
            points=nasa_points,
            nasa_observations=nasa_obs,
            metadata={"assumed_H0_kms_mpc": 70.0, "cosmology": "Flat Lambda-CDM"},
        )
        with open(nasa_json, "w", encoding="utf-8") as f:
            json.dump(nasa_spec.model_dump(), f, indent=2)

        with open(nasa_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["independent_variable", "observed_value", "uncertainty", "label"])
            for p in nasa_points:
                writer.writerow([p.independent_variable, p.observed_value, p.uncertainty, p.label])

    # 4. NIST CODATA 2022
    nist_json = FIXTURES_DIR / "nist_codata_2022.json"
    nist_csv = FIXTURES_DIR / "nist_codata_2022.csv"
    if not nist_json.exists():
        constants = [
            NISTPhysicalConstant(
                constant_symbol="c",
                constant_name="speed of light in vacuum",
                value=299792458.0,
                standard_uncertainty=0.0,
                unit="m / s",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="h",
                constant_name="Planck constant",
                value=6.62607015e-34,
                standard_uncertainty=0.0,
                unit="J * s",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="hbar",
                constant_name="reduced Planck constant",
                value=1.0545718176461565e-34,
                standard_uncertainty=0.0,
                unit="J * s",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="e",
                constant_name="elementary charge",
                value=1.602176634e-19,
                standard_uncertainty=0.0,
                unit="C",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="k_B",
                constant_name="Boltzmann constant",
                value=1.380649e-23,
                standard_uncertainty=0.0,
                unit="J / K",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="N_A",
                constant_name="Avogadro constant",
                value=6.02214076e23,
                standard_uncertainty=0.0,
                unit="1 / mol",
                relative_uncertainty=0.0,
                codata_year=2022,
                is_exact=True,
            ),
            NISTPhysicalConstant(
                constant_symbol="G",
                constant_name="Newtonian constant of gravitation",
                value=6.67430e-11,
                standard_uncertainty=1.5e-15,
                unit="m^3 / (kg * s^2)",
                relative_uncertainty=2.2e-5,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="m_e",
                constant_name="electron mass",
                value=9.1093837139e-31,
                standard_uncertainty=2.8e-40,
                unit="kg",
                relative_uncertainty=3.0e-10,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="m_p",
                constant_name="proton mass",
                value=1.67262192595e-27,
                standard_uncertainty=5.2e-37,
                unit="kg",
                relative_uncertainty=3.1e-10,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="alpha",
                constant_name="fine-structure constant",
                value=7.2973525643e-3,
                standard_uncertainty=1.1e-12,
                unit="dimensionless",
                relative_uncertainty=1.5e-10,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="eps_0",
                constant_name="vacuum electric permittivity",
                value=8.8541878128e-12,
                standard_uncertainty=1.3e-21,
                unit="F / m",
                relative_uncertainty=1.5e-10,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="mu_0",
                constant_name="vacuum magnetic permeability",
                value=1.25663706212e-6,
                standard_uncertainty=1.9e-16,
                unit="N / A^2",
                relative_uncertainty=1.5e-10,
                codata_year=2022,
                is_exact=False,
            ),
            NISTPhysicalConstant(
                constant_symbol="R_inf",
                constant_name="Rydberg constant",
                value=10973731.568157,
                standard_uncertainty=0.000012,
                unit="1 / m",
                relative_uncertainty=1.1e-12,
                codata_year=2022,
                is_exact=False,
            ),
        ]
        nist_points = [
            EmpiricalDataPoint(
                independent_variable=float(i),
                observed_value=c.value,
                uncertainty=c.standard_uncertainty,
                label=c.constant_symbol,
                metadata={"name": c.constant_name, "unit": c.unit, "is_exact": c.is_exact},
            )
            for i, c in enumerate(constants)
        ]
        nist_spec = EmpiricalDatasetSpec(
            dataset_id="nist-codata-2022-fundamental-constants",
            dataset_name="NIST CODATA 2022 Recommended Values of Fundamental Physical Constants",
            dataset_type=EmpiricalDatasetType.NIST_PHYSICAL_CONSTANTS,
            source_reference="NIST Special Publication 961 / CODATA 2022 Recommended Values",
            description="Internationally recommended values of fundamental physical constants from NIST CODATA 2022",
            independent_variable_symbol="index",
            dependent_variable_symbol="value",
            tolerance_sigma=3.0,
            points=nist_points,
            nist_constants=constants,
            metadata={"codata_edition": 2022, "si_system": "2019 redefinition"},
        )
        with open(nist_json, "w", encoding="utf-8") as f:
            json.dump(nist_spec.model_dump(), f, indent=2)

        with open(nist_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["independent_variable", "observed_value", "uncertainty", "label"])
            for p in nist_points:
                writer.writerow([p.independent_variable, p.observed_value, p.uncertainty, p.label])


@lru_cache(maxsize=16)
def load_cern_z_resonance() -> EmpiricalDatasetSpec:
    """Loads CERN Z0 boson invariant mass & resonance distribution."""
    ensure_fixtures_exist()
    filepath = FIXTURES_DIR / "cern_z_resonance.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return EmpiricalDatasetSpec.model_validate(data)


@lru_cache(maxsize=16)
def load_cern_higgs_resonance() -> EmpiricalDatasetSpec:
    """Loads CERN Higgs boson invariant mass distribution."""
    ensure_fixtures_exist()
    filepath = FIXTURES_DIR / "cern_higgs_resonance.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return EmpiricalDatasetSpec.model_validate(data)


@lru_cache(maxsize=16)
def load_nasa_hubble_supernovae() -> EmpiricalDatasetSpec:
    """Loads NASA Hubble Space Telescope Type Ia supernova dataset."""
    ensure_fixtures_exist()
    filepath = FIXTURES_DIR / "nasa_hubble_supernovae.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return EmpiricalDatasetSpec.model_validate(data)


@lru_cache(maxsize=16)
def load_nist_codata_2022() -> EmpiricalDatasetSpec:
    """Loads NIST CODATA 2022 recommended fundamental physical constants."""
    ensure_fixtures_exist()
    filepath = FIXTURES_DIR / "nist_codata_2022.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return EmpiricalDatasetSpec.model_validate(data)


# Backward-compatible convenience aliases
def load_mock_cern_dataset() -> EmpiricalDatasetSpec:
    return load_cern_higgs_resonance()


def load_mock_nasa_dataset() -> EmpiricalDatasetSpec:
    return load_nasa_hubble_supernovae()


def load_mock_nist_dataset() -> EmpiricalDatasetSpec:
    return load_nist_codata_2022()


def get_available_mocks() -> List[str]:
    return [
        "cern_higgs_resonance",
        "cern_z_resonance",
        "nasa_hubble_supernovae",
        "nist_codata_2022",
    ]


def load_mock_by_name(name: str) -> EmpiricalDatasetSpec:
    name_clean = name.lower().replace("-", "_")
    if "z" in name_clean:
        return load_cern_z_resonance()
    elif "higgs" in name_clean:
        return load_cern_higgs_resonance()
    elif "hubble" in name_clean or "nasa" in name_clean or "supernova" in name_clean:
        return load_nasa_hubble_supernovae()
    elif "nist" in name_clean or "codata" in name_clean or "planck" in name_clean:
        return load_nist_codata_2022()
    elif "cern" in name_clean:
        return load_cern_higgs_resonance()
    else:
        raise FileNotFoundError(f"Mock dataset '{name}' not found. Available: {get_available_mocks()}")
