from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from shared.schemas.finding_result import FindingResult, FindingState, LayerFinding, TargetEntityType
from shared.schemas.physical_invariants import SystemContext
from shared.schemas.empirical_data import EmpiricalDatasetSpec
from shared.schemas.epistemic_logic import ClaimGraph


class ValidationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str


class ValidationFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    job_id: str
    state: str
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool


class EquationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str
    latex_raw: str
    canonical_ast_json: Dict[str, Any]
    sympy_expr: Optional[str] = None


class EquationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version_id: str
    label: str
    latex_raw: str
    canonical_ast_json: Dict[str, Any]
    sympy_expr: Optional[str] = None
    created_at: str


class VariableCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    symbol: str
    name: str
    unit: str
    domain: str = "real"
    latex_presentation: Optional[str] = None


class VariableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version_id: str
    symbol: str
    name: str
    unit: str
    domain: str
    latex_presentation: Optional[str] = None
    created_at: str


class EquationVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    expression_ast: Optional[ExprNode] = None
    variables: List[VariableSpec] = Field(default_factory=list)
    units: List[UnitSpec] = Field(default_factory=list)
    system_context: Optional[SystemContext] = None
    empirical_dataset: Optional[EmpiricalDatasetSpec] = None
    empirical_tolerance_sigma: float = 3.0
    claim_graph: Optional[ClaimGraph] = None
    target_entity_type: Optional[TargetEntityType] = TargetEntityType.EQUATION
    target_entity_id: Optional[str] = "interactive"
    version_id: Optional[str] = None


class ValidationFindingDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    layer: int
    target_entity_type: str
    target_entity_id: str
    job_id: str
    state: str
    diagnostic_code: str
    message: str
    symbolic_simplification: Optional[str] = None
    dimensions_verified: bool
    diagnostics: Any = Field(default_factory=list)
    created_at: str


class ValidationRunDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version_id: str
    status: str
    overall_state: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    findings: List[ValidationFindingDetailResponse] = Field(default_factory=list)
