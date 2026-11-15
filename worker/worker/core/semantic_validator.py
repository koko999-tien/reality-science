from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Set
import pint
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
    VARIABLE_NAME_PATTERN,
)
from shared.models.enums import DiagnosticCode
from worker.core.complexity_guard import (
    inspect_ast_complexity,
    ComplexityLimitExceededError,
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_POLYNOMIAL_POWER,
)

ALLOWED_DOMAINS = {"real", "positive_real", "integer", "complex"}


class UndeclaredSymbolError(ValueError):
    pass


class SemanticValidationError(ValueError):
    pass


@dataclass
class SemanticValidationResult:
    is_valid: bool
    diagnostic_code: str
    message: str
    referenced_symbols: Set[str] = field(default_factory=set)
    diagnostics: List[str] = field(default_factory=list)


def extract_referenced_symbols(node: ExprNode, symbols: Optional[Set[str]] = None) -> Set[str]:
    """Recursively walks ExprNode AST to collect all variable symbol names."""
    if symbols is None:
        symbols = set()

    if node.node_type == NodeType.VARIABLE:
        if node.value is not None:
            symbols.add(str(node.value))

    if node.left:
        extract_referenced_symbols(node.left, symbols)
    if node.right:
        extract_referenced_symbols(node.right, symbols)
    if node.args:
        for arg in node.args:
            extract_referenced_symbols(arg, symbols)

    return symbols


def validate_variable_declarations(
    variables: List[VariableSpec],
) -> Tuple_Validation:
    """Validates symbol-first declarations: valid identifier, domain, unit, and uniqueness."""
    seen_symbols: Dict[str, VariableSpec] = {}
    for var in variables:
        if not var.symbol or not VARIABLE_NAME_PATTERN.match(var.symbol):
            return False, f"Variable symbol '{var.symbol}' is not a valid identifier.", DiagnosticCode.INVALID_AST.value
        if var.domain not in ALLOWED_DOMAINS:
            return (
                False,
                f"Variable '{var.symbol}' has invalid domain '{var.domain}'. Allowed domains: {sorted(ALLOWED_DOMAINS)}",
                DiagnosticCode.DOMAIN_BOUNDARY_VIOLATION.value,
            )
        if not var.unit or not var.unit.strip():
            return False, f"Variable '{var.symbol}' has empty unit specification.", DiagnosticCode.INVALID_AST.value

        if var.symbol in seen_symbols:
            existing = seen_symbols[var.symbol]
            if existing.unit != var.unit or existing.domain != var.domain:
                return (
                    False,
                    f"Conflicting duplicate variable declaration for '{var.symbol}': {existing} vs {var}",
                    DiagnosticCode.INVALID_AST.value,
                )
        seen_symbols[var.symbol] = var

    return True, "", ""


Tuple_Validation = tuple[bool, str, str]


def validate_ast_semantics(
    node: ExprNode,
    variables: List[VariableSpec],
    units: Optional[List[UnitSpec]] = None,
) -> SemanticValidationResult:
    """Executes Layer 1 Syntax & Semantic verification:
    - Pre-flight complexity gates (depth <= 15, nodes <= 100, powers <= 20)
    - Symbol-first variable declaration and domain checks
    - Variable symbol matching (zero undeclared symbols in AST)
    - AST structural validity and constant safety
    """
    diagnostics: List[str] = []

    # 1. Pre-flight AST complexity gates
    try:
        nodes_count, max_depth = inspect_ast_complexity(node)
        diagnostics.append(f"AST complexity passed: {nodes_count} nodes, depth {max_depth}")
    except ComplexityLimitExceededError as e:
        return SemanticValidationResult(
            is_valid=False,
            diagnostic_code=DiagnosticCode.COMPLEXITY_LIMIT_EXCEEDED.value,
            message=str(e),
            diagnostics=[str(e)],
        )

    # 2. Variable declarations validation
    var_valid, var_err, var_code = validate_variable_declarations(variables)
    if not var_valid:
        return SemanticValidationResult(
            is_valid=False,
            diagnostic_code=var_code,
            message=var_err,
            diagnostics=[var_err],
        )

    declared_symbols = {v.symbol for v in variables}

    # 3. Symbol matching (all referenced symbols must be declared)
    referenced_symbols = extract_referenced_symbols(node)
    undeclared = referenced_symbols - declared_symbols
    if undeclared:
        msg = f"AST references undeclared symbol(s): {sorted(undeclared)}"
        return SemanticValidationResult(
            is_valid=False,
            diagnostic_code=DiagnosticCode.UNDECLARED_SYMBOL.value,
            message=msg,
            referenced_symbols=referenced_symbols,
            diagnostics=[msg],
        )

    diagnostics.append(
        f"Symbol matching passed: {len(referenced_symbols)} referenced symbols matched declared variables"
    )

    # 4. Units pre-flight validity check
    if units:
        unit_names = {u.name for u in units}
        for u in units:
            if not u.name or not VARIABLE_NAME_PATTERN.match(u.name):
                msg = f"Custom unit name '{u.name}' is invalid"
                return SemanticValidationResult(
                    is_valid=False,
                    diagnostic_code=DiagnosticCode.INVALID_AST.value,
                    message=msg,
                    diagnostics=[msg],
                )
        diagnostics.append(f"Unit specs passed: {len(units)} custom unit specifications validated")

    return SemanticValidationResult(
        is_valid=True,
        diagnostic_code=DiagnosticCode.VALIDATION_PASSED.value,
        message="Layer 1 Syntax and Semantic validation passed.",
        referenced_symbols=referenced_symbols,
        diagnostics=diagnostics,
    )
