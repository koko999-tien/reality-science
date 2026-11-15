"""Pydantic schemas for the Backend Evidence Lab module (Feature 25)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.empirical_data import EmpiricalDatasetSpec, EmpiricalDatasetType


class DatasetUploadRequest(BaseModel):
    """Optional metadata provided when uploading empirical datasets."""

    model_config = ConfigDict(extra="ignore")

    dataset_name: Optional[str] = Field(default=None, description="Title of the dataset")
    dataset_type: Optional[EmpiricalDatasetType] = Field(default=None, description="Type: CERN, NASA, NIST, or CUSTOM")
    source_reference: Optional[str] = Field(default=None, description="DOI, publication citation, or source catalog")
    description: Optional[str] = Field(default=None, description="Descriptive summary")
    independent_variable_symbol: Optional[str] = Field(default=None, description="Independent variable symbol (e.g. x, E, z)")
    dependent_variable_symbol: Optional[str] = Field(default=None, description="Dependent variable symbol (e.g. y, mu, cross_section)")
    tolerance_sigma: float = Field(default=3.0, ge=0.1, le=10.0, description="Tolerance threshold in standard errors")


class DatasetIngestResponse(BaseModel):
    """Response returned upon successful ingestion of an empirical dataset."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(..., description="Unique dataset identifier")
    dataset_name: str = Field(..., description="Title of the ingested dataset")
    dataset_type: str = Field(..., description="Dataset classification type")
    point_count: int = Field(..., ge=0, description="Total number of validated observation points")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 fingerprint of payload")
    message: str = Field(default="Dataset ingested and registered successfully")


class ValidationReportResponse(BaseModel):
    """Detailed validation report for pre-upload dry runs."""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if schema and data points are compliant")
    point_count: int = Field(default=0, ge=0, description="Count of parsed valid points")
    dataset_type: str = Field(..., description="Inferred or declared dataset type")
    x_range: Optional[Tuple[float, float]] = Field(default=None, description="Range [min, max] of independent coordinate")
    y_range: Optional[Tuple[float, float]] = Field(default=None, description="Range [min, max] of dependent coordinate")
    errors: List[str] = Field(default_factory=list, description="Validation errors preventing ingestion")
    warnings: List[str] = Field(default_factory=list, description="Advisory validation warnings")


class MockDatasetListItem(BaseModel):
    """Descriptor for standard synthetic benchmarks available in Evidence Lab."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Mock identifier key for retrieval")
    title: str = Field(..., description="Human-readable title")
    type: str = Field(..., description="Dataset classification")
    point_count: int = Field(..., description="Number of reference points")
    description: Optional[str] = Field(default=None, description="Scientific context and source description")


class MockDatasetListResponse(BaseModel):
    """List response of available synthetic mock benchmarks."""

    model_config = ConfigDict(extra="forbid")

    mocks: List[MockDatasetListItem] = Field(default_factory=list)
