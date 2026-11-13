from typing import Dict, List, Tuple
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from worker.core.dimension_engine import evaluate_ast_dimensions, DimensionalityCheckError


def execute_dimensional_verification(
    expression_ast: ExprNode,
    variables: List[VariableSpec],
    units: List[UnitSpec],
) -> Tuple[bool, str, str]:
    """Verifies dimensional consistency of expression AST using Pint.

    Returns:
        (success, dimensionality_str, diagnostic_code_or_message)
    """
    var_map: Dict[str, VariableSpec] = {v.symbol: v for v in variables}
    unit_map: Dict[str, UnitSpec] = {u.name: u for u in units}

    try:
        quantity = evaluate_ast_dimensions(expression_ast, var_map, unit_map)
        return True, str(quantity.dimensionality), "VALIDATION_PASSED"
    except DimensionalityCheckError as e:
        return False, "", "DIMENSIONAL_MISMATCH"
    except Exception as e:
        return False, "", f"DIMENSIONAL_ERROR: {str(e)}"
