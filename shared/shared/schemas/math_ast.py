from __future__ import annotations
from enum import Enum
import re
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

NUMERIC_STRING_PATTERN = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")
VARIABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


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

    @field_validator("value", mode="before")
    @classmethod
    def reject_booleans_in_value(cls, v: object) -> object:
        if isinstance(v, bool):
            raise ValueError("Boolean values are forbidden for mathematical AST value")
        return v

    @model_validator(mode="after")
    def validate_node_semantics(self) -> "ExprNode":
        if self.node_type == NodeType.CONSTANT:
            if self.value is None:
                raise ValueError("Constant node value cannot be None")
            if isinstance(self.value, (int, float)):
                return self
            if isinstance(self.value, str):
                if not NUMERIC_STRING_PATTERN.match(self.value.strip()):
                    raise ValueError(f"Constant string value must be a valid numeric literal: {self.value}")
                return self
            raise ValueError(f"Invalid constant type: {type(self.value).__name__}")

        elif self.node_type == NodeType.VARIABLE:
            if self.value is None:
                raise ValueError("Variable node value cannot be None")
            if not isinstance(self.value, str):
                raise ValueError(f"Variable symbol must be a string, got {type(self.value).__name__}")
            if not VARIABLE_NAME_PATTERN.match(self.value):
                raise ValueError(f"Variable symbol '{self.value}' must be a valid identifier (e.g. x, v_0)")
            return self

        elif self.node_type == NodeType.UNARY_OP:
            if self.op is None:
                raise ValueError("Unary operation requires 'op' field")
            if self.left is None:
                raise ValueError("Unary operation requires 'left' operand")

        elif self.node_type == NodeType.BINARY_OP:
            if self.op is None:
                raise ValueError("Binary operation requires 'op' field")
            if self.left is None or self.right is None:
                raise ValueError("Binary operation requires both 'left' and 'right' operands")

        elif self.node_type == NodeType.FUNCTION_CALL:
            if self.func is None:
                raise ValueError("Function call requires 'func' field")
            if not self.args or len(self.args) == 0:
                raise ValueError("Function call requires at least one argument in 'args'")

        return self


ExprNode.model_rebuild()
