from typing import Tuple
from shared.schemas.math_ast import ExprNode, NodeType, OperatorType

MAX_AST_DEPTH = 15
MAX_AST_NODES = 100
MAX_POLYNOMIAL_POWER = 20


class ComplexityLimitExceededError(ValueError):
    pass


def inspect_ast_complexity(node: ExprNode, current_depth: int = 1) -> Tuple[int, int]:
    """Recursively measures node count and depth, asserting against complexity bombs.

    Returns:
        (total_nodes, max_depth)
    """
    if current_depth > MAX_AST_DEPTH:
        raise ComplexityLimitExceededError(
            f"AST depth {current_depth} exceeds maximum limit of {MAX_AST_DEPTH}"
        )

    nodes = 1
    max_d = current_depth

    # Check power operator limits to prevent exponential expansion bombs
    if node.node_type == NodeType.BINARY_OP and node.op == OperatorType.POW:
        if node.right and node.right.node_type == NodeType.CONSTANT:
            if isinstance(node.right.value, (int, float)) and node.right.value > MAX_POLYNOMIAL_POWER:
                raise ComplexityLimitExceededError(
                    f"Exponent {node.right.value} exceeds maximum limit of {MAX_POLYNOMIAL_POWER}"
                )

    children = []
    if node.left:
        children.append(node.left)
    if node.right:
        children.append(node.right)
    if node.args:
        children.extend(node.args)

    for child in children:
        child_nodes, child_depth = inspect_ast_complexity(child, current_depth + 1)
        nodes += child_nodes
        if child_depth > max_d:
            max_d = child_depth

    if nodes > MAX_AST_NODES:
        raise ComplexityLimitExceededError(
            f"AST total nodes {nodes} exceeds maximum limit of {MAX_AST_NODES}"
        )

    return nodes, max_d
