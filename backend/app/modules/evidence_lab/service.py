"""Evidence Lab Service: dataset parsing, validation, and registry management (Feature 25)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evidence_lab.models import EvidenceArtifact
from app.modules.evidence_lab.schemas import (
    DatasetUploadRequest,
    MockDatasetListItem,
    MockDatasetListResponse,
    ValidationReportResponse,
)
from shared.fixtures.empirical.loader import (
    get_available_mocks,
    load_mock_by_name,
)
from shared.schemas.empirical_data import (
    EmpiricalDataPoint,
    EmpiricalDatasetSpec,
    EmpiricalDatasetType,
)

# In-memory repository for uploaded datasets (fast, thread-safe, isolated)
_DATASET_STORE: Dict[str, Tuple[EmpiricalDatasetSpec, str]] = {}


async def register_evidence_artifact(
    db: AsyncSession, project_id: str, storage_path: str, sha256_hash: str, description: str = ""
) -> EvidenceArtifact:
    """Registers an immutable research evidence artifact in PostgreSQL."""
    artifact = EvidenceArtifact(
        project_id=project_id,
        storage_path=storage_path,
        sha256_hash=sha256_hash,
        description=description,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


def compute_sha256(data: bytes) -> str:
    """Computes SHA-256 hexadecimal hash string."""
    return hashlib.sha256(data).hexdigest()


def extract_file_and_params_from_request(
    raw_bytes: bytes, content_type: str
) -> Tuple[bytes, str, Dict[str, str]]:
    """Extracts uploaded file bytes, filename, and form parameters from raw HTTP request.

    Uses Python standard library parser without requiring external python-multipart.
    """
    if not raw_bytes:
        return b"", "", {}

    if "multipart/form-data" in content_type:
        from email.parser import BytesParser

        msg = BytesParser().parsebytes(
            b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + raw_bytes
        )
        file_bytes = b""
        filename = ""
        params: Dict[str, str] = {}
        file_found = False
        if msg.is_multipart():
            for part in msg.get_payload():
                cd = part.get("content-disposition", "")
                fn = part.get_filename()
                payload = part.get_payload(decode=True) or b""
                if fn or "filename=" in cd:
                    file_bytes = payload
                    filename = fn or "uploaded_file"
                    file_found = True
                else:
                    name_param = part.get_param("name", header="content-disposition")
                    if name_param:
                        params[name_param] = payload.decode("utf-8", errors="ignore").strip()
        if file_found:
            return file_bytes, filename, params
        return file_bytes, filename, params

    return raw_bytes, "", {}


def parse_and_validate_dataset_json(
    raw_bytes: bytes, metadata: Optional[DatasetUploadRequest] = None
) -> Tuple[EmpiricalDatasetSpec, str]:
    """Parses and validates raw JSON payload into an EmpiricalDatasetSpec."""
    sha256 = compute_sha256(raw_bytes)
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Malformed JSON payload: {str(e)}") from e

    if not isinstance(data, dict):
        raise ValueError("JSON payload root must be an object")

    # Overlay metadata if provided
    if metadata:
        if metadata.dataset_name and "dataset_name" not in data and "name" not in data:
            data["dataset_name"] = metadata.dataset_name
        if metadata.dataset_type and "dataset_type" not in data and "source_type" not in data:
            data["dataset_type"] = metadata.dataset_type.value
        if metadata.source_reference and "source_reference" not in data and "source" not in data:
            data["source_reference"] = metadata.source_reference
        if metadata.description and "description" not in data:
            data["description"] = metadata.description
        if metadata.independent_variable_symbol and "independent_variable_symbol" not in data:
            data["independent_variable_symbol"] = metadata.independent_variable_symbol
        if metadata.dependent_variable_symbol and "dependent_variable_symbol" not in data:
            data["dependent_variable_symbol"] = metadata.dependent_variable_symbol

    # Ensure dataset_id exists
    if "dataset_id" not in data or not data["dataset_id"]:
        data["dataset_id"] = f"dataset-{uuid.uuid4().hex[:12]}"
    if "dataset_name" not in data and "name" not in data:
        data["dataset_name"] = "Imported Empirical Dataset"
    if "dataset_type" not in data and "source_type" not in data:
        data["dataset_type"] = EmpiricalDatasetType.CUSTOM.value

    dataset = EmpiricalDatasetSpec.model_validate(data)
    return dataset, sha256


def parse_and_validate_dataset_csv(
    raw_bytes: bytes, metadata: Optional[DatasetUploadRequest] = None
) -> Tuple[EmpiricalDatasetSpec, str]:
    """Parses and validates tabular CSV payload into an EmpiricalDatasetSpec."""
    sha256 = compute_sha256(raw_bytes)
    try:
        text = raw_bytes.decode("utf-8-sig")
    except Exception as e:
        raise ValueError(f"CSV encoding error: {str(e)}") from e

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file is completely empty")

    header = [h.strip().lower() for h in rows[0]]
    data_rows = rows[1:]
    if not data_rows:
        raise ValueError("CSV file contains header but no data rows")

    # Column identification heuristics
    x_col: Optional[int] = None
    y_col: Optional[int] = None
    sigma_col: Optional[int] = None
    label_col: Optional[int] = None

    x_aliases = ["independent_variable", "x", "energy", "energy_gev", "redshift", "redshift_z", "frequency", "time", "index"]
    y_aliases = ["observed_value", "y_obs", "y", "cross_section", "cross_section_pb", "distance_modulus", "distance_modulus_mu", "value", "measurement_value", "flux"]
    sigma_aliases = ["uncertainty", "sigma", "error", "uncertainty_gev", "measurement_error", "distance_modulus_error", "err"]
    label_aliases = ["label", "name", "target_name", "symbol", "id", "observation_id"]

    for idx, col_name in enumerate(header):
        if x_col is None and col_name in x_aliases:
            x_col = idx
        elif y_col is None and col_name in y_aliases:
            y_col = idx
        elif sigma_col is None and col_name in sigma_aliases:
            sigma_col = idx
        elif label_col is None and col_name in label_aliases:
            label_col = idx

    # Fallback to positional columns if headers not recognized
    if x_col is None:
        x_col = 0
    if y_col is None:
        y_col = 1 if len(header) > 1 else 0
    if sigma_col is None and len(header) > 2:
        sigma_col = 2
    if label_col is None and len(header) > 3:
        label_col = 3

    points: List[EmpiricalDataPoint] = []
    for row_idx, row in enumerate(data_rows, start=2):
        if not row or all(c.strip() == "" for c in row):
            continue  # skip empty lines

        if len(row) <= max(x_col, y_col):
            raise ValueError(f"Row {row_idx} has insufficient columns (expected at least {max(x_col, y_col) + 1})")

        try:
            x_val = float(row[x_col].strip())
            y_val = float(row[y_col].strip())
        except (ValueError, TypeError) as err:
            raise ValueError(f"Row {row_idx}: non-numeric value in coordinates: {err}") from err

        sigma_val = 0.0
        if sigma_col is not None and len(row) > sigma_col and row[sigma_col].strip():
            try:
                sigma_val = float(row[sigma_col].strip())
            except (ValueError, TypeError) as err:
                raise ValueError(f"Row {row_idx}: non-numeric uncertainty: {err}") from err

        label_val = None
        if label_col is not None and len(row) > label_col and row[label_col].strip():
            label_val = row[label_col].strip()

        points.append(
            EmpiricalDataPoint(
                independent_variable=x_val,
                observed_value=y_val,
                uncertainty=sigma_val,
                label=label_val,
            )
        )

    if not points:
        raise ValueError("No valid observation points found in CSV")

    ds_name = metadata.dataset_name if metadata and metadata.dataset_name else "CSV Ingested Dataset"
    ds_type = metadata.dataset_type if metadata and metadata.dataset_type else EmpiricalDatasetType.CUSTOM
    indep_sym = metadata.independent_variable_symbol if metadata and metadata.independent_variable_symbol else (header[x_col] if x_col < len(header) else "x")
    dep_sym = metadata.dependent_variable_symbol if metadata and metadata.dependent_variable_symbol else (header[y_col] if y_col < len(header) else "y")
    tolerance = metadata.tolerance_sigma if metadata and metadata.tolerance_sigma else 3.0

    dataset = EmpiricalDatasetSpec(
        dataset_id=f"csv-dataset-{uuid.uuid4().hex[:12]}",
        dataset_name=ds_name,
        dataset_type=ds_type,
        source_reference=metadata.source_reference if metadata else None,
        description=metadata.description if metadata else None,
        independent_variable_symbol=indep_sym,
        dependent_variable_symbol=dep_sym,
        tolerance_sigma=tolerance,
        points=points,
    )
    return dataset, sha256


def register_empirical_dataset(dataset: EmpiricalDatasetSpec, sha256_hash: str) -> str:
    """Stores a validated dataset in the runtime store."""
    _DATASET_STORE[dataset.dataset_id] = (dataset, sha256_hash)
    return dataset.dataset_id


def get_empirical_dataset(dataset_id: str) -> Optional[EmpiricalDatasetSpec]:
    """Retrieves an empirical dataset from storage or standard benchmarks."""
    if dataset_id in _DATASET_STORE:
        return _DATASET_STORE[dataset_id][0]

    # Check if dataset_id matches any standard mock
    try:
        return load_mock_by_name(dataset_id)
    except FileNotFoundError:
        return None


def validate_dataset_payload(raw_bytes: bytes, filename: str) -> ValidationReportResponse:
    """Dry-run validation for uploaded empirical datasets without persistence."""
    errors: List[str] = []
    warnings: List[str] = []
    dataset: Optional[EmpiricalDatasetSpec] = None

    stripped = raw_bytes.strip()
    is_json = (
        filename.lower().endswith(".json")
        or stripped.startswith(b"{")
        or stripped.startswith(b"[")
    )
    is_csv = not is_json and (filename.lower().endswith(".csv") or b"," in raw_bytes[:200])
    try:
        if is_csv:
            dataset, _ = parse_and_validate_dataset_csv(raw_bytes)
        else:
            dataset, _ = parse_and_validate_dataset_json(raw_bytes)
    except Exception as e:
        errors.append(f"Parse error: {str(e)}")

    if errors or dataset is None:
        return ValidationReportResponse(
            is_valid=False,
            point_count=0,
            dataset_type="unknown",
            errors=errors,
            warnings=warnings,
        )

    x, y, s = dataset.to_xy_sigma()
    point_count = len(x)
    if point_count == 0:
        errors.append("Dataset contains 0 observation points.")
    elif point_count < 2 and dataset.dataset_type != EmpiricalDatasetType.NIST_PHYSICAL_CONSTANTS:
        warnings.append("Sample size N < 2: statistical degrees of freedom will be limited.")

    x_range = (float(min(x)), float(max(x))) if x else None
    y_range = (float(min(y)), float(max(y))) if y else None

    # Check uncertainties
    zero_unc_count = sum(1 for val in s if val == 0.0)
    if zero_unc_count > 0 and dataset.dataset_type != EmpiricalDatasetType.NIST_PHYSICAL_CONSTANTS:
        warnings.append(f"{zero_unc_count} points have uncertainty = 0.0; sample RMSE fallback will be applied.")

    return ValidationReportResponse(
        is_valid=len(errors) == 0,
        point_count=point_count,
        dataset_type=dataset.dataset_type.value,
        x_range=x_range,
        y_range=y_range,
        errors=errors,
        warnings=warnings,
    )


def list_mock_datasets() -> MockDatasetListResponse:
    """Lists standard synthetic benchmarks available in Evidence Lab."""
    items = [
        MockDatasetListItem(
            name="cern_z_resonance",
            title="CERN LHC Z0 Boson Resonance Distribution",
            type="cern_particle_collision",
            point_count=13,
            description="Relativistic Breit-Wigner resonance distribution centered at M_Z = 91.1876 GeV in dimuon decay channel",
        ),
        MockDatasetListItem(
            name="cern_higgs_resonance",
            title="CERN LHC Higgs Boson Invariant Mass Distribution",
            type="cern_particle_collision",
            point_count=13,
            description="Diphoton invariant mass peak centered at 125.09 GeV over exponential continuum background",
        ),
        MockDatasetListItem(
            name="nasa_hubble_supernovae",
            title="NASA Hubble Space Telescope Type Ia Supernova Survey",
            type="nasa_astrophysical",
            point_count=13,
            description="Cosmological redshift vs distance modulus observations of standard candle Type Ia supernovae",
        ),
        MockDatasetListItem(
            name="nist_codata_2022",
            title="NIST CODATA 2022 Fundamental Physical Constants",
            type="nist_physical_constants",
            point_count=13,
            description="Internationally recommended values for fundamental constants (c, h, G, e, k_B, m_e, etc.)",
        ),
    ]
    return MockDatasetListResponse(mocks=items)


def get_mock_dataset(name: str) -> EmpiricalDatasetSpec:
    """Fetches a standard benchmark by name."""
    return load_mock_by_name(name)
