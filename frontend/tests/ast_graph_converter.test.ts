import { graphToAst, astToGraph, TranslationError } from "@/lib/ast_graph_converter";
import { ExprNode, VariableSpec } from "@/types/contracts";
import {
  MathCanvasNode,
  MathCanvasEdge,
  ConstantNode,
  VariableNode,
  BinaryOpNode,
  UnaryOpNode,
  FunctionCallNode,
  EquationRootNode,
} from "@/types/canvas";

describe("ast_graph_converter", () => {
  const declaredVariables: VariableSpec[] = [
    { symbol: "x", name: "Position", unit: "meter", domain: "real" },
    { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real" },
    { symbol: "t", name: "Time", unit: "second", domain: "positive_real" },
    { symbol: "m", name: "Mass", unit: "kilogram", domain: "positive_real" },
  ];

  describe("graphToAst - Leaf Nodes", () => {
    it("converts a single constant node to ExprNode", () => {
      const nodes: MathCanvasNode[] = [
        {
          id: "n1",
          type: "constantNode",
          position: { x: 0, y: 0 },
          data: { value: 42.5 },
        },
      ];
      const edges: MathCanvasEdge[] = [];

      const ast = graphToAst(nodes, edges, declaredVariables);
      expect(ast).toEqual({
        node_type: "constant",
        value: 42.5,
      });
    });

    it("throws error if constant node has non-numeric value", () => {
      const nodes: MathCanvasNode[] = [
        {
          id: "n1",
          type: "constantNode",
          position: { x: 0, y: 0 },
          data: { value: "invalid-number" },
        },
      ];
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(/Invalid constant value/);
    });

    it("converts a declared variable node to ExprNode", () => {
      const nodes: MathCanvasNode[] = [
        {
          id: "n1",
          type: "variableNode",
          position: { x: 0, y: 0 },
          data: { symbol: "v" },
        },
      ];
      const ast = graphToAst(nodes, [], declaredVariables);
      expect(ast).toEqual({
        node_type: "variable",
        value: "v",
      });
    });

    it("rejects undeclared variable symbols", () => {
      const nodes: MathCanvasNode[] = [
        {
          id: "n1",
          type: "variableNode",
          position: { x: 0, y: 0 },
          data: { symbol: "undeclared_var" },
        },
      ];
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(
        /Symbol 'undeclared_var' is undeclared/
      );
    });

    it("throws error if variable node has empty symbol", () => {
      const nodes: MathCanvasNode[] = [
        {
          id: "n1",
          type: "variableNode",
          position: { x: 0, y: 0 },
          data: { symbol: "" },
        },
      ];
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(
        /Variable node has no symbol selected/
      );
    });
  });

  describe("graphToAst - Binary Operations & Handle Connections", () => {
    it("converts a binary addition node with left and right children", () => {
      const nodes: MathCanvasNode[] = [
        { id: "c1", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 10 } },
        { id: "v1", type: "variableNode", position: { x: 0, y: 50 }, data: { symbol: "x" } },
        { id: "op1", type: "binaryOpNode", position: { x: 100, y: 25 }, data: { op: "+" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "c1", sourceHandle: "output", target: "op1", targetHandle: "left" },
        { id: "e2", source: "v1", sourceHandle: "output", target: "op1", targetHandle: "right" },
      ];

      const ast = graphToAst(nodes, edges, declaredVariables);
      expect(ast).toEqual({
        node_type: "binary_op",
        op: "+",
        left: { node_type: "constant", value: 10 },
        right: { node_type: "variable", value: "x" },
      });
    });

    it("throws error when binary operator is missing left operand", () => {
      const nodes: MathCanvasNode[] = [
        { id: "v1", type: "variableNode", position: { x: 0, y: 50 }, data: { symbol: "x" } },
        { id: "op1", type: "binaryOpNode", position: { x: 100, y: 25 }, data: { op: "*" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e2", source: "v1", sourceHandle: "output", target: "op1", targetHandle: "right" },
      ];

      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(
        /missing left operand/
      );
    });

    it("throws error when binary operator is missing right operand", () => {
      const nodes: MathCanvasNode[] = [
        { id: "c1", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 5 } },
        { id: "op1", type: "binaryOpNode", position: { x: 100, y: 25 }, data: { op: "/" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "c1", sourceHandle: "output", target: "op1", targetHandle: "left" },
      ];

      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(
        /missing right operand/
      );
    });
  });

  describe("graphToAst - Unary and Function Call Nodes", () => {
    it("converts unary negation", () => {
      const nodes: MathCanvasNode[] = [
        { id: "v1", type: "variableNode", position: { x: 0, y: 0 }, data: { symbol: "v" } },
        { id: "neg1", type: "unaryOpNode", position: { x: 100, y: 0 }, data: { op: "neg" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "v1", sourceHandle: "output", target: "neg1", targetHandle: "left" },
      ];

      const ast = graphToAst(nodes, edges, declaredVariables);
      expect(ast).toEqual({
        node_type: "unary_op",
        op: "neg",
        left: { node_type: "variable", value: "v" },
      });
    });

    it("converts function call (sqrt)", () => {
      const nodes: MathCanvasNode[] = [
        { id: "c1", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 16 } },
        { id: "f1", type: "functionCallNode", position: { x: 100, y: 0 }, data: { func: "sqrt" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "c1", sourceHandle: "output", target: "f1", targetHandle: "arg0" },
      ];

      const ast = graphToAst(nodes, edges, declaredVariables);
      expect(ast).toEqual({
        node_type: "function_call",
        func: "sqrt",
        args: [{ node_type: "constant", value: 16 }],
      });
    });
  });

  describe("graphToAst - EquationRootNode Integration", () => {
    it("follows EquationRootNode to expression source", () => {
      const nodes: MathCanvasNode[] = [
        { id: "c1", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 99 } },
        { id: "root1", type: "equationRootNode", position: { x: 200, y: 0 }, data: { name: "R" } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "c1", sourceHandle: "output", target: "root1", targetHandle: "input" },
      ];

      const ast = graphToAst(nodes, edges, declaredVariables);
      expect(ast).toEqual({
        node_type: "constant",
        value: 99,
      });
    });

    it("throws error if EquationRootNode has no incoming connection", () => {
      const nodes: MathCanvasNode[] = [
        { id: "root1", type: "equationRootNode", position: { x: 200, y: 0 }, data: { name: "R" } },
      ];
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, [], declaredVariables)).toThrow(
        /Root node is not connected to an expression/
      );
    });
  });

  describe("graphToAst - Cycle Detection & Complexity Guards", () => {
    it("detects and rejects graph cycles", () => {
      // Create cycle: op1 -> op2 -> op1
      const nodes: MathCanvasNode[] = [
        { id: "op1", type: "binaryOpNode", position: { x: 0, y: 0 }, data: { op: "+" } },
        { id: "op2", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "*" } },
        { id: "c1", type: "constantNode", position: { x: 0, y: 100 }, data: { value: 1 } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e1", source: "op2", sourceHandle: "output", target: "op1", targetHandle: "left" },
        { id: "e2", source: "c1", sourceHandle: "output", target: "op1", targetHandle: "right" },
        { id: "e3", source: "op1", sourceHandle: "output", target: "op2", targetHandle: "left" },
        { id: "e4", source: "c1", sourceHandle: "output", target: "op2", targetHandle: "right" },
      ];

      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(
        /Cyclic graph detected/
      );
    });

    it("detects cycles reachable from an EquationRootNode", () => {
      // Root -> op1 -> op2 -> op1
      const nodes: MathCanvasNode[] = [
        { id: "root1", type: "equationRootNode", position: { x: 300, y: 0 }, data: { name: "R" } },
        { id: "op1", type: "binaryOpNode", position: { x: 200, y: 0 }, data: { op: "+" } },
        { id: "op2", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "*" } },
        { id: "c1", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 2 } },
      ];
      const edges: MathCanvasEdge[] = [
        { id: "e0", source: "op1", sourceHandle: "output", target: "root1", targetHandle: "input" },
        { id: "e1", source: "op2", sourceHandle: "output", target: "op1", targetHandle: "left" },
        { id: "e2", source: "c1", sourceHandle: "output", target: "op1", targetHandle: "right" },
        { id: "e3", source: "op1", sourceHandle: "output", target: "op2", targetHandle: "left" },
        { id: "e4", source: "c1", sourceHandle: "output", target: "op2", targetHandle: "right" },
      ];

      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(
        /Cyclic graph detected/
      );
    });

    it("enforces depth guardrail (max 15)", () => {
      // Build a chain of 17 unary operators
      const nodes: MathCanvasNode[] = [];
      const edges: MathCanvasEdge[] = [];

      nodes.push({
        id: "c0",
        type: "constantNode",
        position: { x: 0, y: 0 },
        data: { value: 1 },
      });

      for (let i = 1; i <= 17; i++) {
        nodes.push({
          id: `neg_${i}`,
          type: "unaryOpNode",
          position: { x: i * 50, y: 0 },
          data: { op: "neg" },
        });
        const prevId = i === 1 ? "c0" : `neg_${i - 1}`;
        edges.push({
          id: `e_${i}`,
          source: prevId,
          sourceHandle: "output",
          target: `neg_${i}`,
          targetHandle: "left",
        });
      }

      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(TranslationError);
      expect(() => graphToAst(nodes, edges, declaredVariables)).toThrow(
        /AST recursion depth exceeded guardrail limit/
      );
    });
  });

  describe("astToGraph & Round-Trip Parity", () => {
    it("converts AST to graph and round-trips back to identical AST", () => {
      // Complex formula: sqrt(x ** 2 + v ** 2)
      const originalAst: ExprNode = {
        node_type: "function_call",
        func: "sqrt",
        args: [
          {
            node_type: "binary_op",
            op: "+",
            left: {
              node_type: "binary_op",
              op: "**",
              left: { node_type: "variable", value: "x" },
              right: { node_type: "constant", value: 2 },
            },
            right: {
              node_type: "binary_op",
              op: "**",
              left: { node_type: "variable", value: "v" },
              right: { node_type: "constant", value: 2 },
            },
          },
        ],
      };

      const { nodes, edges } = astToGraph(originalAst, declaredVariables);

      // Verify graph structure
      expect(nodes.length).toBeGreaterThan(0);
      expect(edges.length).toBeGreaterThan(0);
      expect(nodes.some((n) => n.type === "equationRootNode")).toBe(true);

      // Verify round-trip conversion parity
      const roundTripAst = graphToAst(nodes, edges, declaredVariables);
      expect(roundTripAst).toEqual(originalAst);
    });

    it("round-trips unary negation inside binary division", () => {
      // Formula: -(x) / t
      const originalAst: ExprNode = {
        node_type: "binary_op",
        op: "/",
        left: {
          node_type: "unary_op",
          op: "neg",
          left: { node_type: "variable", value: "x" },
        },
        right: { node_type: "variable", value: "t" },
      };

      const { nodes, edges } = astToGraph(originalAst, declaredVariables);
      const roundTripAst = graphToAst(nodes, edges, declaredVariables);
      expect(roundTripAst).toEqual(originalAst);
    });
  });
});
