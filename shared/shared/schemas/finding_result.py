from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FindingState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NEEDS_EXPERT_REVIEW = "NEEDS_EXPERT_REVIEW"
    NOT_YET_TESTED = "NOT_YET_TESTED"


class TargetEntityType(str, Enum):
    EQUATION = "EQUATION"
    VARIABLE = "VARIABLE"
    CLAIM = "CLAIM"


class LayerFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: int = Field(..., ge=1, le=6)
    name: str
    state: FindingState
    diagnostic_code: str
    message: str
    diagnostics: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None


class FindingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    # Optional for legacy/non-queue producers; mandatory at queue ingestion.
    version_id: Optional[str] = None
    target_entity_type: Optional[TargetEntityType] = None
    target_entity_id: Optional[str] = None
    bundle_sha256: Optional[str] = None
    state: FindingState
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool
    diagnostics: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None
    layer: Optional[int] = None
    layer_findings: Optional[Dict[int, LayerFinding]] = None


class PipelineValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    version_id: Optional[str] = None
    target_entity_type: TargetEntityType = TargetEntityType.EQUATION
    target_entity_id: str = "interactive"
    overall_state: FindingState
    summary: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool = False
    layers: Dict[int, LayerFinding] = Field(default_factory=dict)
    diagnostics: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0
