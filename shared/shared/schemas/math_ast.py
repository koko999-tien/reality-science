from __future__ import annotations
from enum import Enum
import math
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
                if isinstance(self.value, float) and not math.isfinite(self.value):
                    raise ValueError(f"Constant floating-point value must be finite, got: {self.value}")
                return self
            if isinstance(self.value, str):
                trimmed = self.value.strip()
                if not NUMERIC_STRING_PATTERN.match(trimmed):
                    raise ValueError(f"Constant string value must be a valid numeric literal: {self.value}")
                try:
                    val = float(trimmed)
                    if not math.isfinite(val):
                        raise ValueError(f"Constant numeric string must evaluate to a finite number: {self.value}")
                except (ValueError, OverflowError) as err:
                    raise ValueError(f"Constant numeric string must evaluate to a finite number: {self.value}") from err
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
            if not self.args or len(self.args) != 1:
                raise ValueError(f"Function {self.func} requires exactly one argument in 'args'")

        return self


ExprNode.model_rebuild()


def try_eval_constant_ast(node: ExprNode) -> Optional[float]:
    """Recursively evaluates an AST subtree if and only if it consists entirely of
    numeric constants, unary/binary arithmetic operations, and allowed functions.

    Returns float value if statically evaluatable, or None if it references
    variables, encounters division by zero, or overflows.
    """
    if node.node_type == NodeType.CONSTANT:
        if node.value is None:
            return None
        try:
            val = float(node.value)
            return val if math.isfinite(val) else None
        except (ValueError, TypeError, OverflowError):
            return None

    elif node.node_type == NodeType.VARIABLE:
        return None

    elif node.node_type == NodeType.UNARY_OP:
        if not node.left:
            return None
        val = try_eval_constant_ast(node.left)
        if val is None:
            return None
        if node.op == OperatorType.NEG:
            return -val
        return None

    elif node.node_type == NodeType.BINARY_OP:
        if not node.left or not node.right:
            return None
        lv = try_eval_constant_ast(node.left)
        rv = try_eval_constant_ast(node.right)
        if lv is None or rv is None:
            return None
        try:
            if node.op == OperatorType.ADD:
                res = lv + rv
            elif node.op == OperatorType.SUB:
                res = lv - rv
            elif node.op == OperatorType.MUL:
                res = lv * rv
            elif node.op == OperatorType.DIV:
                if rv == 0:
                    return None
                res = lv / rv
            elif node.op == OperatorType.POW:
                # Prevent massive memory consumption during float exponentiation
                if abs(rv) > 10000:
                    return None
                res = lv ** rv
            else:
                return None
            return res if math.isfinite(res) else None
        except (OverflowError, ZeroDivisionError, ValueError):
            return None

    elif node.node_type == NodeType.FUNCTION_CALL:
        if not node.args or len(node.args) != 1:
            return None
        argv = try_eval_constant_ast(node.args[0])
        if argv is None:
            return None
        try:
            if node.func == AllowedFunction.SQRT:
                if argv < 0:
                    return None
                res = math.sqrt(argv)
            elif node.func == AllowedFunction.SIN:
                res = math.sin(argv)
            elif node.func == AllowedFunction.COS:
                res = math.cos(argv)
            elif node.func == AllowedFunction.EXP:
                res = math.exp(argv)
            elif node.func == AllowedFunction.LOG:
                if argv <= 0:
                    return None
                res = math.log(argv)
            else:
                return None
            return res if math.isfinite(res) else None
        except (OverflowError, ValueError):
            return None

    return None

