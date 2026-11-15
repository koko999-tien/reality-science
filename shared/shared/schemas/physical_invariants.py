from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PhysicalConstraintType(str, Enum):
    SPEED_OF_LIGHT = "SPEED_OF_LIGHT"
    ENERGY_CONSERVATION = "ENERGY_CONSERVATION"
    MOMENTUM_CONSERVATION = "MOMENTUM_CONSERVATION"


class SafetyPolicy(str, Enum):
    STRICT_REJECT = "strict_reject"
    PERMISSIVE_FLAG = "permissive_flag"


class SystemContext(BaseModel):
    """Physical system assumptions and boundary condition declarations."""
    model_config = ConfigDict(extra="forbid")

    is_closed_system: bool = True
    is_relativistic: bool = False
    has_external_forces: bool = False
    has_external_heat_or_work: bool = False
    safety_policy: str = Field(default="strict_reject")
    assumptions: List[str] = Field(default_factory=list)

    @field_validator("safety_policy")
    @classmethod
    def validate_safety_policy(cls, v: str) -> str:
        valid_policies = {p.value for p in SafetyPolicy}
        if v not in valid_policies:
            raise ValueError(f"safety_policy must be one of {valid_policies}, got '{v}'")
        return v


class PhysicalConstraintSpec(BaseModel):
    """Specification of an active physical constraint/law."""
    model_config = ConfigDict(extra="forbid")

    constraint_type: str
    name: str
    description: Optional[str] = None
    threshold: Optional[float] = None
    unit: Optional[str] = None
    is_active: bool = True


class PhysicalFindingDetails(BaseModel):
    """Structured diagnostics for Layer 4 physical invariant evaluation."""
    model_config = ConfigDict(extra="forbid")

    invariant_type: str
    violated_symbols: List[str] = Field(default_factory=list)
    calculated_value: Optional[float] = None
    limit_value: Optional[float] = None
    system_assumptions: Dict[str, Any] = Field(default_factory=dict)
    details: Dict[str, Any] = Field(default_factory=dict)
