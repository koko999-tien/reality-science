from __future__ import annotations
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class NodeType(str, Enum):
    CONSTANT = "constant"
    VARIABLE = "variable"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION_CALL = "function_call"


class OperatorType(str, Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    POW = "**"
    NEG = "neg"


class AllowedFunction(str, Enum):
    SQRT = "sqrt"
    SIN = "sin"
    COS = "cos"
    EXP = "exp"
    LOG = "log"


class UnitSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    symbol: str
    dimensionality: str  # e.g., '[length] ** 2 / [time]'
    scale_factor: float = 1.0


class VariableSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    symbol: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    name: str
    unit: str
    domain: str = Field(default="real", pattern=r"^(real|positive_real|integer|complex)$")
    latex_presentation: Optional[str] = None


class ExprNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_type: NodeType
    value: Optional[Union[float, int, str]] = None
    op: Optional[OperatorType] = None
    func: Optional[AllowedFunction] = None
    left: Optional[ExprNode] = None
    right: Optional[ExprNode] = None
    args: Optional[List[ExprNode]] = None


ExprNode.model_rebuild()
