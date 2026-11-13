from typing import Tuple, Set
import sympy as sp
from shared.schemas.math_ast import ExprNode
from worker.core.ast_evaluator import (
    ast_to_sympy,
    UndeclaredSymbolError,
    MathematicalSingularityError,
)
from worker.core.complexity_guard import (
    inspect_ast_complexity,
    ComplexityLimitExceededError,
)


def execute_symbolic_evaluation(
    expression_ast: ExprNode,
    declared_symbols: Set[str],
) -> Tuple[bool, str, str]:
    """Inspects complexity, parses AST into SymPy, and computes symbolic simplification.

    Returns:
        (success, simplified_latex_or_str, diagnostic_code_or_message)
    """
    try:
        inspect_ast_complexity(expression_ast)
        sympy_expr = ast_to_sympy(expression_ast, declared_symbols)
        simplified = sp.simplify(sympy_expr)
        return True, str(simplified), "VALIDATION_PASSED"
    except ComplexityLimitExceededError as e:
        return False, "", "COMPLEXITY_LIMIT_EXCEEDED"
    except UndeclaredSymbolError as e:
        return False, "", "UNDECLARED_SYMBOL"
    except MathematicalSingularityError as e:
        return False, "", "SINGULARITY_OR_DIVISION_BY_ZERO"
    except Exception as e:
        return False, "", f"SYMBOLIC_ERROR: {str(e)}"
