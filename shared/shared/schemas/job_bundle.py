from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from shared.schemas.finding_result import FindingResult, FindingState, TargetEntityType
from shared.schemas.physical_invariants import SystemContext
from shared.schemas.empirical_data import EmpiricalDatasetSpec
from shared.schemas.epistemic_logic import ClaimGraph


class JobBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    version_id: str
    target_entity_type: TargetEntityType
    target_entity_id: str
    expression_ast: Optional[ExprNode] = None
    variables: List[VariableSpec] = Field(default_factory=list)
    units: List[UnitSpec] = Field(default_factory=list)
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    system_context: Optional[SystemContext] = None
    empirical_dataset: Optional[EmpiricalDatasetSpec] = None
    empirical_tolerance_sigma: float = Field(default=3.0, ge=0.1, le=10.0)
    claim_graph: Optional[ClaimGraph] = None


__all__ = ["JobBundle", "TargetEntityType"]
