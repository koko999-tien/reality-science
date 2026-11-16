"""Evidence Lab REST API Endpoints (Feature 25).

Provides endpoints for empirical dataset ingestion, schema validation,
benchmark listing, and dataset retrieval.
"""

from __future__ import annotations

import json
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.modules.evidence_lab.schemas import (
    DatasetIngestResponse,
    DatasetUploadRequest,
    MockDatasetListResponse,
    ValidationReportResponse,
)
from app.modules.evidence_lab.service import (
    extract_file_and_params_from_request,
    get_empirical_dataset,
    get_mock_dataset,
    list_mock_datasets,
    parse_and_validate_dataset_csv,
    parse_and_validate_dataset_json,
    register_empirical_dataset,
    validate_dataset_payload,
)
from shared.schemas.empirical_data import EmpiricalDatasetSpec, EmpiricalDatasetType

router = APIRouter(prefix="/evidence", tags=["evidence-lab"])
MAX_DATASET_REQUEST_BYTES = 10 * 1024 * 1024


async def read_limited_request_body(request: Request) -> bytes:
    """Read dataset requests incrementally and reject oversized payloads."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_DATASET_REQUEST_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Dataset request exceeds the 10 MiB limit",
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length header",
            ) from exc

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_DATASET_REQUEST_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Dataset request exceeds the 10 MiB limit",
            )
        body.extend(chunk)
    return bytes(body)


@router.post(
    "/upload",
    response_model=DatasetIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest an empirical observation dataset (JSON or CSV)",
)
async def upload_dataset(
    request: Request,
    dataset_name: Optional[str] = Query(None),
    dataset_type: Optional[str] = Query(None),
    source_reference: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    independent_variable_symbol: Optional[str] = Query(None),
    dependent_variable_symbol: Optional[str] = Query(None),
    tolerance_sigma: float = Query(3.0),
) -> DatasetIngestResponse:
    """Uploads and ingests a CERN, NASA, NIST, or custom empirical dataset.

    Accepts structured JSON matching EmpiricalDatasetSpec or tabular CSV files.
    Calculates cryptographic SHA-256 fingerprint, performs schema validation,
    and registers dataset for RCE Layer 5 correlation.
    """
    raw_body = await read_limited_request_body(request)
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    content_type = request.headers.get("content-type", "")
    file_bytes, filename, form_params = extract_file_and_params_from_request(raw_body, content_type)

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Resolve metadata from form params or query params
    name_val = form_params.get("dataset_name") or dataset_name
    type_str = form_params.get("dataset_type") or dataset_type
    ref_val = form_params.get("source_reference") or source_reference
    desc_val = form_params.get("description") or description
    indep_val = form_params.get("independent_variable_symbol") or independent_variable_symbol
    dep_val = form_params.get("dependent_variable_symbol") or dependent_variable_symbol

    tol_val = tolerance_sigma
    if "tolerance_sigma" in form_params:
        try:
            tol_val = float(form_params["tolerance_sigma"])
        except ValueError:
            pass

    req_type = None
    if type_str:
        try:
            req_type = EmpiricalDatasetType(type_str)
        except ValueError:
            pass

    metadata = DatasetUploadRequest(
        dataset_name=name_val,
        dataset_type=req_type,
        source_reference=ref_val,
        description=desc_val,
        independent_variable_symbol=indep_val,
        dependent_variable_symbol=dep_val,
        tolerance_sigma=tol_val,
    )

    stripped = file_bytes.strip()
    is_json = (
        filename.lower().endswith(".json")
        or "application/json" in content_type
        or stripped.startswith(b"{")
        or stripped.startswith(b"[")
    )
    is_csv = not is_json and (
        filename.lower().endswith(".csv")
        or "text/csv" in content_type
        or b"," in file_bytes[:200]
    )

    try:
        if is_csv:
            dataset, sha256_hash = parse_and_validate_dataset_csv(file_bytes, metadata)
        else:
            dataset, sha256_hash = parse_and_validate_dataset_json(file_bytes, metadata)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset validation failure: {str(e)}",
        ) from e

    # Register in runtime repository
    dataset.dataset_id = f"dataset-{uuid4().hex}"
    try:
        register_empirical_dataset(dataset, sha256_hash)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset ID already exists",
        ) from exc
    x, y, s = dataset.to_xy_sigma()

    return DatasetIngestResponse(
        dataset_id=dataset.dataset_id,
        dataset_name=dataset.dataset_name,
        dataset_type=dataset.dataset_type.value,
        point_count=len(x),
        sha256_hash=sha256_hash,
        message=f"Dataset '{dataset.dataset_name}' successfully ingested ({len(x)} points).",
    )


@router.post(
    "/validate",
    response_model=ValidationReportResponse,
    summary="Validate empirical dataset payload without saving (dry-run)",
)
async def validate_dataset(
    request: Request,
) -> ValidationReportResponse:
    """Dry-run validation reporting schema compliance, coordinate ranges, and warnings."""
    raw_body = await read_limited_request_body(request)
    if not raw_body:
        return ValidationReportResponse(
            is_valid=False,
            point_count=0,
            dataset_type="unknown",
            errors=["Uploaded payload is completely empty"],
        )

    content_type = request.headers.get("content-type", "")
    file_bytes, filename, _ = extract_file_and_params_from_request(raw_body, content_type)
    if not file_bytes:
        return ValidationReportResponse(
            is_valid=False,
            point_count=0,
            dataset_type="unknown",
            errors=["Uploaded payload is completely empty"],
        )

    return validate_dataset_payload(file_bytes, filename or "")


@router.get(
    "/mocks",
    response_model=MockDatasetListResponse,
    summary="List available standard synthetic observation benchmarks",
)
async def list_mocks() -> MockDatasetListResponse:
    """Returns standard reference benchmarks (CERN Z0, CERN Higgs, NASA Hubble, NIST CODATA 2022)."""
    return list_mock_datasets()


@router.get(
    "/mocks/{mock_name}",
    response_model=EmpiricalDatasetSpec,
    summary="Fetch standard reference benchmark dataset by name",
)
async def fetch_mock_dataset(mock_name: str) -> EmpiricalDatasetSpec:
    """Retrieves full specification and observation data points for a named benchmark."""
    try:
        return get_mock_dataset(mock_name)
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.get(
    "/datasets/{dataset_id}",
    response_model=EmpiricalDatasetSpec,
    summary="Retrieve an ingested empirical dataset by ID",
)
async def fetch_dataset(dataset_id: str) -> EmpiricalDatasetSpec:
    """Retrieves a previously ingested empirical dataset from runtime storage."""
    dataset = get_empirical_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empirical dataset '{dataset_id}' not found",
        )
    return dataset


__all__ = ["router"]
