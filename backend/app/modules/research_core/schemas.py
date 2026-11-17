
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec, NodeType, OperatorType, try_eval_constant_ast


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    title: str
    description: str | None = None
    visibility: str = "private_draft"


class ResearchVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    version_number: int
    title: str
    content_hash: str | None = None
    publication_status: str
    is_frozen: bool
    revision: int = 0
    created_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    title: str
    description: str | None = None
    owner_actor_id: str
    visibility: str
    is_frozen: bool
    created_at: datetime
    versions: list[ResearchVersionResponse] = Field(default_factory=list)
    can_edit: bool = False


class VersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)


class DraftEquation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = Field(default=None, max_length=36)
    label: str = Field(min_length=1, max_length=100)
    latex_raw: str = Field(max_length=100000)
    canonical_ast_json: ExprNode


class DraftVariable(VariableSpec):
    symbol: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$", max_length=50)
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=100)
    latex_presentation: str | None = Field(default=None, max_length=100)


class DraftSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)
    equations: list[DraftEquation] = Field(max_length=100)
    variables: list[DraftVariable] = Field(max_length=500)
    units: list[UnitSpec] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_declarations(self):
        import math
        for names, kind in (([v.symbol for v in self.variables], "variable symbol"),
                            ([u.name for u in self.units], "unit name"),
                            ([e.id for e in self.equations if e.id], "equation ID")):
            if len(set(names)) != len(names):
                raise ValueError(f"Duplicate {kind}")
        if any(not math.isfinite(u.scale_factor) or u.scale_factor <= 0 for u in self.units):
            raise ValueError("Unit scale factors must be positive and finite")
        declared = {v.symbol for v in self.variables}
        for equation in self.equations:
            count = 0
            stack = [(equation.canonical_ast_json, 1)]
            while stack:
                node, depth = stack.pop()
                count += 1
                if depth > 15 or count > 100:
                    raise ValueError("AST exceeds the 15-depth / 100-node limit")
                if node.node_type == NodeType.VARIABLE and node.value not in declared:
                    raise ValueError(f"Undeclared symbol: {node.value}")
                allowed = {
                    NodeType.CONSTANT: {"node_type", "value"}, NodeType.VARIABLE: {"node_type", "value"},
                    NodeType.UNARY_OP: {"node_type", "op", "left"},
                    NodeType.BINARY_OP: {"node_type", "op", "left", "right"},
                    NodeType.FUNCTION_CALL: {"node_type", "func", "args"},
                }[node.node_type]
                if set(node.model_dump(exclude_none=True)) - allowed:
                    raise ValueError("AST node has operands or fields incompatible with its type")
                if node.node_type == NodeType.UNARY_OP and node.op != OperatorType.NEG:
                    raise ValueError("Unary operator must be neg")
                if node.node_type == NodeType.BINARY_OP and node.op == OperatorType.NEG:
                    raise ValueError("Binary operator cannot be neg")
                if node.op == OperatorType.POW:
                    power = try_eval_constant_ast(node.right, max_depth=15)
                    if power is not None and abs(power) > 20:
                        raise ValueError("Exponent exceeds maximum magnitude 20")
                stack.extend((child, depth + 1) for child in [node.left, node.right, *(node.args or [])] if child)
        return self


class DraftSnapshot(BaseModel):
    version: ResearchVersionResponse
    equations: list[dict]
    variables: list[dict]
    units: list[UnitSpec]
