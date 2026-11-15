from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict

from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from shared.schemas.finding_result import FindingState
from shared.models.enums import ClaimType, ClaimRelationType


class RelationType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    EQUIVALENT_TO = "EQUIVALENT_TO"
    CHALLENGES = "CHALLENGES"
    SUPERSEDES = "SUPERSEDES"
    RELATED_TO = "RELATED_TO"
    EXTENDS = "EXTENDS"
    REPRODUCES = "REPRODUCES"
    REPLICATES = "REPLICATES"


class DependencyLogic(str, Enum):
    ALL = "ALL"  # Conjunction: all antecedent premises must hold
    ANY = "ANY"  # Disjunction: at least one antecedent premise must hold


class ContradictionType(str, Enum):
    DIRECT_EQUALITY = "DIRECT_EQUALITY"
    BOUNDARY_CONFLICT = "BOUNDARY_CONFLICT"
    SIGN_CONFLICT = "SIGN_CONFLICT"
    EXPLICIT_CONTRADICTION = "EXPLICIT_CONTRADICTION"
    DOMAIN_INCOMPATIBILITY = "DOMAIN_INCOMPATIBILITY"


class ClaimSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., description="Unique claim identifier e.g. UUID or code")
    claim_code: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Human-readable claim code e.g. CLM-001")
    claim_type: ClaimType
    statement: str = Field(..., min_length=3, description="Verbal or formal scientific assertion")
    target_variable: Optional[str] = Field(default=None, description="Physical variable governed by this claim")
    expression_ast: Optional[ExprNode] = Field(default=None, description="Mathematical AST of the claim proposition")
    assumptions: List[str] = Field(default_factory=list, description="Explicit contextual assumptions")
    local_state: FindingState = Field(default=FindingState.NOT_YET_TESTED, description="State from L1-L5 checks")
    propagated_state: Optional[FindingState] = Field(default=None, description="State after epistemic graph propagation")
    dependency_logic: DependencyLogic = Field(default=DependencyLogic.ALL)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    uncertainty_notes: Optional[str] = Field(default=None, description="Explanatory notes regarding uncertainty")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClaimDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_claim_id: str = Field(..., description="Dependent claim (consequent)")
    target_claim_id: str = Field(..., description="Prerequisite claim (antecedent)")
    relation_type: RelationType = Field(default=RelationType.DEPENDS_ON)
    justification: Optional[str] = Field(default=None, description="Deductive or empirical justification")
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class CycleReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cycle_detected: bool
    cycles: List[List[str]] = Field(default_factory=list, description="Ordered cycle paths of claim_ids")
    cyclic_claim_ids: Set[str] = Field(default_factory=set, description="Set of claim_ids participating in any cycle")


class ContradictionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contradiction_type: ContradictionType
    claim_id_a: str
    claim_id_b: str
    conflict_variable: Optional[str] = None
    description: str
    symbolic_proof: Optional[str] = None
    severity: FindingState = Field(default=FindingState.FAIL)


class ContradictionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contradictions_found: bool
    items: List[ContradictionItem] = Field(default_factory=list)


class EpistemicFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    state: FindingState
    diagnostic_code: str
    message: str
    antecedent_failures: List[str] = Field(default_factory=list)
    cycle_membership: Optional[List[str]] = None
    contradictions: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)


class ClaimGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    version_id: str
    claims: List[ClaimSpec] = Field(default_factory=list)
    dependencies: List[ClaimDependency] = Field(default_factory=list)
    variables: List[VariableSpec] = Field(default_factory=list)
    units: List[UnitSpec] = Field(default_factory=list)


class ClaimGraphValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    version_id: str
    overall_state: FindingState
    cycle_report: CycleReport
    contradiction_report: ContradictionReport
    claim_findings: Dict[str, EpistemicFinding] = Field(default_factory=dict)
    topological_order: Optional[List[str]] = None
    diagnostics: List[str] = Field(default_factory=list)
