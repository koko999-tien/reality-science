import { graphToAst, astToGraph, assertCanonicalAst, TranslationError } from "@/lib/ast_graph_converter";
import { ExprNode, VariableSpec } from "@/types/contracts";
import { CANONICAL_PRESETS } from "@/lib/presets";
import { CANONICAL_PRESETS as EDITOR_PRESETS } from "@/components/equations/canvas/ScientificPresetsBar";
import { evaluateAstNumeric } from "@/lib/formula_evaluator";
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

    it("accepts exactly 15 AST levels with or without a visual root", () => {
      let ast: ExprNode = { node_type: "constant", value: 1 };
      for (let level = 1; level < 15; level++) ast = { node_type: "unary_op", op: "neg", left: ast };
      expect(() => assertCanonicalAst(ast)).not.toThrow();
      const graph = astToGraph(ast);
      expect(graphToAst(graph.nodes, graph.edges)).toEqual(ast);
      const root = graph.nodes.find((node) => node.type === "equationRootNode")!;
      expect(graphToAst(graph.nodes.filter((node) => node.id !== root.id), graph.edges.filter((edge) => edge.target !== root.id)))
        .toEqual(ast);
    });

    it("rejects exactly 16 AST levels in stored data and graphs with or without a visual root", () => {
      let ast: ExprNode = { node_type: "constant", value: 1 };
      for (let level = 1; level < 16; level++) ast = { node_type: "unary_op", op: "neg", left: ast };
      expect(() => assertCanonicalAst(ast)).toThrow(/AST recursion depth exceeded/);
      const graph = astToGraph(ast);
      expect(() => graphToAst(graph.nodes, graph.edges)).toThrow(/AST recursion depth exceeded/);
      const root = graph.nodes.find((node) => node.type === "equationRootNode")!;
      expect(() => graphToAst(graph.nodes.filter((node) => node.id !== root.id), graph.edges.filter((edge) => edge.target !== root.id)))
        .toThrow(/AST recursion depth exceeded/);
    });

    it("counts canonical nodes instead of the visual root at the 100-node boundary", () => {
      function tree(leaves: number): ExprNode {
        if (leaves === 1) return { node_type: "constant", value: 1 };
        const left = Math.floor(leaves / 2);
        return { node_type: "binary_op", op: "+", left: tree(left), right: tree(leaves - left) };
      }
      const ast: ExprNode = { node_type: "unary_op", op: "neg", left: tree(50) };
      expect(() => assertCanonicalAst(ast)).not.toThrow();
      const atLimit = astToGraph(ast);
      expect(atLimit.nodes).toHaveLength(101);
      expect(graphToAst(atLimit.nodes, atLimit.edges)).toEqual(ast);
      const tooLarge = astToGraph({ node_type: "unary_op", op: "neg", left: ast });
      expect(() => assertCanonicalAst({ node_type: "unary_op", op: "neg", left: ast })).toThrow(/AST node count exceeded/);
      expect(() => graphToAst(tooLarge.nodes, tooLarge.edges)).toThrow(/AST node count exceeded/);
    });

    it("applies the node limit after expanding a compact shared-operand DAG", () => {
      const nodes: MathCanvasNode[] = [{ id: "n0", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 1 } }];
      const edges: MathCanvasEdge[] = [];
      for (let level = 1; level <= 6; level++) {
        nodes.push({ id: `n${level}`, type: "binaryOpNode", position: { x: 0, y: 0 }, data: { op: "+" } });
        for (const port of ["left", "right"]) {
          edges.push({ id: `${level}-${port}`, source: `n${level - 1}`, sourceHandle: "output", target: `n${level}`, targetHandle: port });
        }
      }
      expect(() => graphToAst(nodes, edges)).toThrow(/AST node count exceeded/);
      expect(() => graphToAst([
        ...nodes,
        { id: "root", type: "equationRootNode", position: { x: 0, y: 0 }, data: { name: "R" } },
      ], [
        ...edges,
        { id: "result", source: "n6", target: "root", sourceHandle: "output", targetHandle: "input" },
      ])).toThrow(/AST node count exceeded/);
    });

    it("accepts the 100-node boundary without a visual root and rejects the 101-node expansion", () => {
      function tree(leaves: number): ExprNode {
        if (leaves === 1) return { node_type: "constant", value: 1 };
        const left = Math.floor(leaves / 2);
        return { node_type: "binary_op", op: "+", left: tree(left), right: tree(leaves - left) };
      }

      const atLimitAst: ExprNode = { node_type: "unary_op", op: "neg", left: tree(50) };
      const atLimitGraph = astToGraph(atLimitAst);
      const root = atLimitGraph.nodes.find((node) => node.type === "equationRootNode")!;
      const withoutRoot = {
        nodes: atLimitGraph.nodes.filter((node) => node.id !== root.id),
        edges: atLimitGraph.edges.filter((edge) => edge.target !== root.id),
      };
      expect(graphToAst(withoutRoot.nodes, withoutRoot.edges)).toEqual(atLimitAst);

      const tooLargeAst: ExprNode = { node_type: "unary_op", op: "neg", left: atLimitAst };
      const tooLargeGraph = astToGraph(tooLargeAst);
      const tooLargeRoot = tooLargeGraph.nodes.find((node) => node.type === "equationRootNode")!;
      expect(() => graphToAst(
        tooLargeGraph.nodes.filter((node) => node.id !== tooLargeRoot.id),
        tooLargeGraph.edges.filter((edge) => edge.target !== tooLargeRoot.id),
      )).toThrow(/AST node count exceeded/);
    });
  });

  describe("whole-canvas integrity", () => {
    const constant = (id: string, value = 1): MathCanvasNode => ({
      id, type: "constantNode", position: { x: 0, y: 0 }, data: { value },
    });
    const root = (id: string): MathCanvasNode => ({
      id, type: "equationRootNode", position: { x: 200, y: 0 }, data: { name: "R" },
    });
    const edge = (id: string, source: string, target: string, targetHandle = "input"): MathCanvasEdge => ({
      id, source, target, sourceHandle: "output", targetHandle,
    });

    it.each([false, true])("rejects extra explicit roots, connected=%s, regardless of order", (connected) => {
      const nodes = [constant("c"), root("r1"), root("r2")];
      const edges = [edge("e1", "c", "r1"), ...(connected ? [edge("e2", "c", "r2")] : [])];
      for (const ordered of [nodes, [...nodes].reverse()]) {
        expect(() => graphToAst(ordered, edges)).toThrow(/Multiple equation roots/);
      }
    });

    it("rejects multiple implicit sinks", () => {
      expect(() => graphToAst([constant("a"), constant("b")], [])).toThrow(/Multiple expression roots/);
    });

    it("rejects a disconnected operand beside a valid expression", () => {
      expect(() => graphToAst([constant("c"), root("r"), constant("orphan")], [edge("e", "c", "r")]))
        .toThrow(/Disconnected.*orphan/);
    });

    it("rejects a disconnected cycle even when there is only one sink", () => {
      const loop: MathCanvasNode = { id: "loop", type: "unaryOpNode", position: { x: 0, y: 0 }, data: { op: "neg" } };
      expect(() => graphToAst([constant("c"), loop], [edge("loop-edge", "loop", "loop", "left")]))
        .toThrow(/Disconnected.*loop/);
    });

    it.each(["source", "target"] as const)("rejects a dangling %s even outside the chosen expression", (endpoint) => {
      const bad = { ...edge("dangling", "c", "r"), [endpoint]: "missing" };
      expect(() => graphToAst([constant("c"), root("r")], [edge("e", "c", "r"), bad]))
        .toThrow(/Edge 'dangling'.*missing/);
    });

    it("rejects duplicate node and edge identities", () => {
      expect(() => graphToAst([constant("c"), constant("c", 2)], [])).toThrow(/Duplicate node ID/);
      expect(() => graphToAst([constant("c"), root("r")], [edge("e", "c", "r"), edge("e", "c", "r")]))
        .toThrow(/Duplicate edge ID/);
    });

    it.each(["input", "left", "right", "arg0"])("rejects duplicate edges to input %s", (port) => {
      const target: MathCanvasNode = port === "input" ? root("r")
        : port === "arg0" ? { id: "r", type: "functionCallNode", position: { x: 0, y: 0 }, data: { func: "sqrt" } }
        : { id: "r", type: "binaryOpNode", position: { x: 0, y: 0 }, data: { op: "+" } };
      expect(() => graphToAst([constant("c"), target], [edge("a", "c", "r", port), edge("b", "c", "r", port)]))
        .toThrow(/Multiple edges.*input/);
    });

    it.each(["sourceHandle", "targetHandle"] as const)("rejects an invalid %s", (handle) => {
      expect(() => graphToAst([constant("c"), root("r")], [{ ...edge("e", "c", "r"), [handle]: "wrong" }]))
        .toThrow(/Invalid .* port/);
    });

    it("rejects incoming edges on leaves and outgoing edges on equation roots", () => {
      expect(() => graphToAst([constant("a"), constant("b")], [edge("e", "a", "b")])).toThrow(/has no input port/);
      expect(() => graphToAst([root("r"), constant("c")], [edge("e", "r", "c")])).toThrow(/has no output port/);
    });

    it("rejects omitted binary input handles instead of inferring a port", () => {
      const nodes: MathCanvasNode[] = [constant("a"), constant("b"), {
        id: "op", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "+" },
      }];
      const edges: MathCanvasEdge[] = [
        { id: "implicit", source: "a", sourceHandle: "output", target: "op" },
        edge("right", "b", "op", "right"),
      ];
      expect(() => graphToAst(nodes, edges)).toThrow(/Invalid target port 'unspecified'/);
    });

    it.each([
      ["equation root", "equationRootNode", "input"],
      ["unary operator", "unaryOpNode", "left"],
      ["function call", "functionCallNode", "arg0"],
    ] as const)("rejects omitted/null and explicit handles on the same %s input", (_, type, handle) => {
      const target: MathCanvasNode = type === "equationRootNode"
        ? root("target")
        : type === "unaryOpNode"
          ? { id: "target", type, position: { x: 100, y: 0 }, data: { op: "neg" } }
          : { id: "target", type, position: { x: 100, y: 0 }, data: { func: "sqrt" } };
      const nodes = [constant("a", 1), constant("b", 2), target];

      for (const implicitHandle of [undefined, null]) {
        const singleInput = graphToAst([nodes[0], target], [{
          id: "only", source: "a", target: "target", targetHandle: implicitHandle,
        }]);
        expect(evaluateAstNumeric(singleInput)).toEqual({ value: type === "unaryOpNode" ? -1 : 1, error: null });
        for (const handles of [[implicitHandle, handle], [handle, implicitHandle]]) {
          const edges: MathCanvasEdge[] = [
            { id: "first", source: "a", sourceHandle: "output", target: "target", targetHandle: handles[0] },
            { id: "second", source: "b", sourceHandle: "output", target: "target", targetHandle: handles[1] },
          ];
          expect(() => graphToAst(nodes, edges)).toThrow(/Multiple edges connect to input/);
        }
      }
    });

    it("rejects a disconnected two-node cycle beside a valid expression", () => {
      const cycleA: MathCanvasNode = { id: "cycle-a", type: "unaryOpNode", position: { x: 0, y: 0 }, data: { op: "neg" } };
      const cycleB: MathCanvasNode = { id: "cycle-b", type: "unaryOpNode", position: { x: 0, y: 0 }, data: { op: "neg" } };
      const nodes = [constant("c"), root("r"), cycleA, cycleB];
      const edges = [
        edge("valid", "c", "r"),
        edge("a-to-b", "cycle-a", "cycle-b", "left"),
        edge("b-to-a", "cycle-b", "cycle-a", "left"),
      ];
      expect(() => graphToAst(nodes, edges)).toThrow(/Disconnected.*cycle-a/);
    });

    it("preserves shared operands and single-port legacy omitted handles", () => {
      const nodes: MathCanvasNode[] = [constant("c", 3), {
        id: "add", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "+" },
      }, root("r")];
      const edges = [edge("l", "c", "add", "left"), edge("r", "c", "add", "right"), { id: "out", source: "add", target: "r" }];
      expect(graphToAst(nodes, edges)).toEqual({
        node_type: "binary_op", op: "+", left: { node_type: "constant", value: 3 }, right: { node_type: "constant", value: 3 },
      });
    });

    it.each(CANONICAL_PRESETS.map((preset) => [preset.id, preset] as const))("preserves preset %s", (_, preset) => {
      const { nodes, edges } = astToGraph(preset.ast, preset.variables);
      expect(graphToAst(nodes, edges, preset.variables)).toEqual(preset.ast);
    });

    it.each(EDITOR_PRESETS.map((preset) => [preset.id, preset] as const))("preserves editor preset %s", (_, preset) => {
      const { nodes, edges } = astToGraph(preset.ast, preset.variables);
      expect(graphToAst(nodes, edges, preset.variables)).toEqual(preset.ast);
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

  describe("shared expressions and operand order", () => {
    const edge = (id: string, source: string, target: string, targetHandle = "input"): MathCanvasEdge => ({
      id, source, target, sourceHandle: "output", targetHandle,
    });

    it("expands a shared non-leaf operand without changing its numeric meaning", () => {
      const nodes: MathCanvasNode[] = [
        { id: "three", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 3 } },
        { id: "one", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 1 } },
        { id: "sum", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op: "+" } },
        { id: "product", type: "binaryOpNode", position: { x: 200, y: 0 }, data: { op: "*" } },
        { id: "r", type: "equationRootNode", position: { x: 300, y: 0 }, data: { name: "R" } },
      ];
      const edges: MathCanvasEdge[] = [
        edge("three-to-sum", "three", "sum", "left"),
        edge("one-to-sum", "one", "sum", "right"),
        edge("sum-to-product-left", "sum", "product", "left"),
        edge("sum-to-product-right", "sum", "product", "right"),
        edge("product-to-root", "product", "r"),
      ];
      const expected: ExprNode = {
        node_type: "binary_op", op: "*",
        left: { node_type: "binary_op", op: "+", left: { node_type: "constant", value: 3 }, right: { node_type: "constant", value: 1 } },
        right: { node_type: "binary_op", op: "+", left: { node_type: "constant", value: 3 }, right: { node_type: "constant", value: 1 } },
      };

      const withoutRoot = {
        nodes: nodes.filter((node) => node.id !== "r"),
        edges: edges.filter((edge) => edge.target !== "r"),
      };
      for (const graph of [{ nodes, edges }, withoutRoot]) {
        for (const orderedNodes of [graph.nodes, [...graph.nodes].reverse()]) {
          for (const orderedEdges of [graph.edges, [...graph.edges].reverse()]) {
            const ast = graphToAst(orderedNodes, orderedEdges);
            expect(ast).toEqual(expected);
            expect(evaluateAstNumeric(ast)).toEqual({ value: 16, error: null });
          }
        }
      }
    });

    it.each([
      ["subtraction", "-", 6],
      ["division", "/", 4],
    ] as const)("preserves left/right operand order for %s", (_, op, expectedValue) => {
      const nodes: MathCanvasNode[] = [
        { id: "left", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 8 } },
        { id: "right", type: "constantNode", position: { x: 0, y: 0 }, data: { value: 2 } },
        { id: "op", type: "binaryOpNode", position: { x: 100, y: 0 }, data: { op } },
        { id: "r", type: "equationRootNode", position: { x: 300, y: 0 }, data: { name: "R" } },
      ];
      const ast = graphToAst(nodes, [
        edge("right-first", "right", "op", "right"),
        edge("left-second", "left", "op", "left"),
        edge("result", "op", "r"),
      ]);
      expect(ast).toEqual({
        node_type: "binary_op", op,
        left: { node_type: "constant", value: 8 },
        right: { node_type: "constant", value: 2 },
      });
      expect(evaluateAstNumeric(ast)).toEqual({ value: expectedValue, error: null });
    });
  });
});
