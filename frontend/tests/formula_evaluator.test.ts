import { evaluateAstNumeric, formatEvaluatedValue } from "@/lib/formula_evaluator";
import { ExprNode } from "@/types/contracts";

describe("Formula Evaluator Engine", () => {
  describe("evaluateAstNumeric - Basic Nodes", () => {
    it("evaluates numeric constant nodes", () => {
      const node: ExprNode = { node_type: "constant", value: 42 };
      const res = evaluateAstNumeric(node, {});
      expect(res.error).toBeNull();
      expect(res.value).toBe(42);
    });

    it("evaluates stringified numeric constant nodes", () => {
      const node: ExprNode = { node_type: "constant", value: "3.14159" };
      const res = evaluateAstNumeric(node, {});
      expect(res.error).toBeNull();
      expect(res.value).toBeCloseTo(3.14159);
    });

    it("returns error for invalid constant value", () => {
      const node: ExprNode = { node_type: "constant", value: "invalid_num" };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBeNull();
      expect(res.error).toContain("Invalid constant value");
    });

    it("evaluates variable node present in scope", () => {
      const node: ExprNode = { node_type: "variable", value: "c" };
      const res = evaluateAstNumeric(node, { c: 299792458 });
      expect(res.error).toBeNull();
      expect(res.value).toBe(299792458);
    });

    it("returns error when variable is missing from scope", () => {
      const node: ExprNode = { node_type: "variable", value: "unknown_sym" };
      const res = evaluateAstNumeric(node, { x: 10 });
      expect(res.value).toBeNull();
      expect(res.error).toContain("Variable 'unknown_sym' has no assigned numerical value");
    });
  });

  describe("evaluateAstNumeric - Binary Operations", () => {
    it("evaluates addition (+)", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "+",
        left: { node_type: "constant", value: 15 },
        right: { node_type: "constant", value: 27 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(42);
    });

    it("evaluates subtraction (-)", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "-",
        left: { node_type: "constant", value: 50 },
        right: { node_type: "constant", value: 8 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(42);
    });

    it("evaluates multiplication (*)", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "constant", value: 6 },
        right: { node_type: "constant", value: 7 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(42);
    });

    it("evaluates division (/)", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "/",
        left: { node_type: "constant", value: 84 },
        right: { node_type: "constant", value: 2 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(42);
    });

    it("catches division by zero singularity", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "/",
        left: { node_type: "constant", value: 10 },
        right: { node_type: "constant", value: 0 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBeNull();
      expect(res.error).toContain("Singularity: division by zero");
    });

    it("evaluates power (**)", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "constant", value: 2 },
        right: { node_type: "constant", value: 8 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(256);
    });

    it("catches domain error on negative base with non-integer exponent", () => {
      const node: ExprNode = {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "constant", value: -4 },
        right: { node_type: "constant", value: 0.5 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBeNull();
      expect(res.error).toContain("Domain error");
    });
  });

  describe("evaluateAstNumeric - Unary and Functions", () => {
    it("evaluates unary negation", () => {
      const node: ExprNode = {
        node_type: "unary_op",
        op: "neg",
        left: { node_type: "constant", value: 42 },
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(-42);
    });

    it("evaluates sqrt function", () => {
      const node: ExprNode = {
        node_type: "function_call",
        func: "sqrt",
        args: [{ node_type: "constant", value: 144 }],
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBe(12);
    });

    it("catches domain error for sqrt of negative number", () => {
      const node: ExprNode = {
        node_type: "function_call",
        func: "sqrt",
        args: [{ node_type: "constant", value: -9 }],
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBeNull();
      expect(res.error).toContain("square root of negative number");
    });

    it("evaluates trig and transcendental functions (sin, cos, exp, log)", () => {
      const sinNode: ExprNode = {
        node_type: "function_call",
        func: "sin",
        args: [{ node_type: "constant", value: 0 }],
      };
      expect(evaluateAstNumeric(sinNode, {}).value).toBe(0);

      const cosNode: ExprNode = {
        node_type: "function_call",
        func: "cos",
        args: [{ node_type: "constant", value: 0 }],
      };
      expect(evaluateAstNumeric(cosNode, {}).value).toBe(1);

      const expNode: ExprNode = {
        node_type: "function_call",
        func: "exp",
        args: [{ node_type: "constant", value: 0 }],
      };
      expect(evaluateAstNumeric(expNode, {}).value).toBe(1);

      const logNode: ExprNode = {
        node_type: "function_call",
        func: "log",
        args: [{ node_type: "constant", value: Math.E }],
      };
      expect(evaluateAstNumeric(logNode, {}).value).toBeCloseTo(1);
    });

    it("catches domain error for log of non-positive number", () => {
      const node: ExprNode = {
        node_type: "function_call",
        func: "log",
        args: [{ node_type: "constant", value: 0 }],
      };
      const res = evaluateAstNumeric(node, {});
      expect(res.value).toBeNull();
      expect(res.error).toContain("logarithm of non-positive number");
    });
  });

  describe("evaluateAstNumeric - Compound Scientific Laws", () => {
    it("evaluates Kinematics equation: v = v_0 + a * t", () => {
      // AST: v_0 + (a * t)
      const ast: ExprNode = {
        node_type: "binary_op",
        op: "+",
        left: { node_type: "variable", value: "v_0" },
        right: {
          node_type: "binary_op",
          op: "*",
          left: { node_type: "variable", value: "a" },
          right: { node_type: "variable", value: "t" },
        },
      };

      const scope = { v_0: 10, a: 9.8, t: 3 };
      const res = evaluateAstNumeric(ast, scope);
      expect(res.error).toBeNull();
      expect(res.value).toBeCloseTo(39.4);
    });

    it("evaluates Einstein Mass-Energy: E = m * c^2", () => {
      const ast: ExprNode = {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "variable", value: "m" },
        right: {
          node_type: "binary_op",
          op: "**",
          left: { node_type: "variable", value: "c" },
          right: { node_type: "constant", value: 2 },
        },
      };

      const scope = { m: 2, c: 3e8 };
      const res = evaluateAstNumeric(ast, scope);
      expect(res.error).toBeNull();
      expect(res.value).toBe(1.8e17);
    });
  });

  describe("formatEvaluatedValue", () => {
    it("formats null or undefined as dash", () => {
      expect(formatEvaluatedValue(null)).toBe("—");
      expect(formatEvaluatedValue(undefined)).toBe("—");
      expect(formatEvaluatedValue(NaN)).toBe("—");
    });

    it("formats standard integers and decimals", () => {
      expect(formatEvaluatedValue(42)).toBe("42");
      expect(formatEvaluatedValue(39.4)).toBe("39.4");
      expect(formatEvaluatedValue(0.1234)).toBe("0.1234");
    });

    it("formats very large or small numbers in scientific notation", () => {
      expect(formatEvaluatedValue(1.8e17)).toBe("1.8000e+17");
      expect(formatEvaluatedValue(6.674e-11)).toBe("6.6740e-11");
    });

    it("formats infinity", () => {
      expect(formatEvaluatedValue(Infinity)).toBe("+∞");
      expect(formatEvaluatedValue(-Infinity)).toBe("-∞");
    });
  });
});
