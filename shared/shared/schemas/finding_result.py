from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FindingState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NEEDS_EXPERT_REVIEW = "NEEDS_EXPERT_REVIEW"
    NOT_YET_TESTED = "NOT_YET_TESTED"


class FindingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    state: FindingState
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool
    diagnostics: List[str] = Field(default_factory=list)
