from __future__ import annotations
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, ConfigDict
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from shared.schemas.finding_result import FindingResult, FindingState


class TargetEntityType(str, Enum):
    EQUATION = "EQUATION"
    VARIABLE = "VARIABLE"
    CLAIM = "CLAIM"


class JobBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    version_id: str
    target_entity_type: TargetEntityType
    target_entity_id: str
    expression_ast: ExprNode
    variables: List[VariableSpec]
    units: List[UnitSpec]
    timeout_seconds: int = Field(default=10, ge=1, le=120)
