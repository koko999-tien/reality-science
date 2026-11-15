import pytest
from shared.schemas.math_ast import (
    AllowedFunction,
    ExprNode,
    NodeType,
    OperatorType,
    UnitSpec,
    VariableSpec,
)
from worker.core.dimension_engine import evaluate_ast_dimensions, DimensionalityCheckError


def test_consistent_dimensions():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_map = {"v": var_v}
    unit_map = {}

    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="v"),
    )
    quantity = evaluate_ast_dimensions(node, var_map, unit_map)
    assert str(quantity.dimensionality) == "[length] / [time]"


def test_dimensional_mismatch():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_t = VariableSpec(symbol="t", name="time", unit="second")
    var_map = {"v": var_v, "t": var_t}
    unit_map = {}

    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.ADD,
        left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    with pytest.raises(DimensionalityCheckError):
        evaluate_ast_dimensions(node, var_map, unit_map)


def test_sqrt_dimensionful_quantity():
    var_a = VariableSpec(symbol="A", name="area", unit="meter ** 2")
    var_map = {"A": var_a}
    node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[ExprNode(node_type=NodeType.VARIABLE, value="A")],
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert str(quantity.dimensionality) == "[length]"


def test_sqrt_velocity_squared():
    var_v = VariableSpec(symbol="v", name="velocity", unit="meter / second")
    var_map = {"v": var_v}
    node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[
            ExprNode(
                node_type=NodeType.BINARY_OP,
                op=OperatorType.POW,
                left=ExprNode(node_type=NodeType.VARIABLE, value="v"),
                right=ExprNode(node_type=NodeType.CONSTANT, value=2),
            )
        ],
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert str(quantity.dimensionality) == "[length] / [time]"


def test_sqrt_dimensionless_quantity():
    node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SQRT,
        args=[ExprNode(node_type=NodeType.CONSTANT, value=4)],
    )
    quantity = evaluate_ast_dimensions(node, {}, {})
    assert quantity.dimensionless


def test_transcendental_functions_dimensionless():
    for fn in [AllowedFunction.SIN, AllowedFunction.COS, AllowedFunction.EXP, AllowedFunction.LOG]:
        node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=fn,
            args=[ExprNode(node_type=NodeType.CONSTANT, value=1)],
        )
        quantity = evaluate_ast_dimensions(node, {}, {})
        assert quantity.dimensionless


def test_transcendental_functions_dimensionful_rejected():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_map = {"x": var_x}
    for fn in [AllowedFunction.SIN, AllowedFunction.COS, AllowedFunction.EXP, AllowedFunction.LOG]:
        node = ExprNode(
            node_type=NodeType.FUNCTION_CALL,
            func=fn,
            args=[ExprNode(node_type=NodeType.VARIABLE, value="x")],
        )
        with pytest.raises(DimensionalityCheckError, match="requires dimensionless input"):
            evaluate_ast_dimensions(node, var_map, {})


def test_compound_constant_exponent_dimensionful_base():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_map = {"x": var_x}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(
            node_type=NodeType.BINARY_OP,
            op=OperatorType.ADD,
            left=ExprNode(node_type=NodeType.CONSTANT, value=1),
            right=ExprNode(node_type=NodeType.CONSTANT, value=1),
        ),
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert str(quantity.dimensionality) == "[length] ** 2"


def test_compound_constant_exponent_negative():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_map = {"x": var_x}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(
            node_type=NodeType.UNARY_OP,
            op=OperatorType.NEG,
            left=ExprNode(node_type=NodeType.CONSTANT, value=1),
        ),
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert str(quantity.dimensionality) == "1 / [length]"


def test_string_constant_exponent_dimensionful_base():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_map = {"x": var_x}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.CONSTANT, value="2"),
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert str(quantity.dimensionality) == "[length] ** 2"


def test_dimensionless_base_variable_exponent():
    var_n = VariableSpec(symbol="n", name="power_param", unit="dimensionless")
    var_map = {"n": var_n}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.CONSTANT, value=2),
        right=ExprNode(node_type=NodeType.VARIABLE, value="n"),
    )
    quantity = evaluate_ast_dimensions(node, var_map, {})
    assert quantity.dimensionless


def test_dimensionful_base_variable_exponent_rejected():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_n = VariableSpec(symbol="n", name="power_param", unit="dimensionless")
    var_map = {"x": var_x, "n": var_n}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="n"),
    )
    with pytest.raises(DimensionalityCheckError, match="requires a statically evaluatable constant exponent"):
        evaluate_ast_dimensions(node, var_map, {})


def test_dimensionful_base_dimensionful_exponent_rejected():
    var_x = VariableSpec(symbol="x", name="position", unit="meter")
    var_t = VariableSpec(symbol="t", name="time", unit="second")
    var_map = {"x": var_x, "t": var_t}
    node = ExprNode(
        node_type=NodeType.BINARY_OP,
        op=OperatorType.POW,
        left=ExprNode(node_type=NodeType.VARIABLE, value="x"),
        right=ExprNode(node_type=NodeType.VARIABLE, value="t"),
    )
    with pytest.raises(DimensionalityCheckError, match="Exponent must be dimensionless"):
        evaluate_ast_dimensions(node, var_map, {})


def test_custom_unit_dynamic_registration():
    custom_unit = UnitSpec(
        name="parsec_custom",
        symbol="pc_custom",
        dimensionality="[length]",
        scale_factor=3.0857e16,
    )
    var_d = VariableSpec(symbol="d", name="distance", unit="parsec_custom")
    var_map = {"d": var_d}
    unit_map = {"parsec_custom": custom_unit}

    node = ExprNode(node_type=NodeType.VARIABLE, value="d")
    quantity = evaluate_ast_dimensions(node, var_map, unit_map)
    assert str(quantity.dimensionality) == "[length]"


def test_transcendental_dimensional_argument_code():
    from worker.tasks.dimensional import execute_dimensional_verification
    from shared.models.enums import DiagnosticCode

    var_m = VariableSpec(symbol="m", name="mass", unit="kilogram")
    node = ExprNode(
        node_type=NodeType.FUNCTION_CALL,
        func=AllowedFunction.SIN,
        args=[ExprNode(node_type=NodeType.VARIABLE, value="m")],
    )
    ok, dim_str, code = execute_dimensional_verification(node, [var_m], [])
    assert ok is False
    assert code == DiagnosticCode.DIMENSIONED_TRANSCENDENTAL_ARGUMENT.value


