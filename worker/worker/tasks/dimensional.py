from typing import Dict, List, Tuple
from celery.exceptions import SoftTimeLimitExceeded
from shared.schemas.math_ast import ExprNode, VariableSpec, UnitSpec
from worker.core.dimension_engine import (
    evaluate_ast_dimensions,
    DimensionalityCheckError,
    TranscendentalDimensionalityError,
)
from shared.models.enums import DiagnosticCode


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
        return True, str(quantity.dimensionality), DiagnosticCode.VALIDATION_PASSED.value
    except TranscendentalDimensionalityError:
        return False, "", DiagnosticCode.DIMENSIONED_TRANSCENDENTAL_ARGUMENT.value
    except DimensionalityCheckError as e:
        if "requires dimensionless input" in str(e):
            return False, "", DiagnosticCode.DIMENSIONED_TRANSCENDENTAL_ARGUMENT.value
        return False, "", DiagnosticCode.DIMENSIONAL_MISMATCH.value
    except SoftTimeLimitExceeded:
        raise
    except Exception as e:
        return False, "", f"DIMENSIONAL_ERROR: {str(e)}"
