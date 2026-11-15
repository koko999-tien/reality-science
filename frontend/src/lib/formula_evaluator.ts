import { ExprNode } from "@/types/contracts";

export interface EvaluationResult {
  value: number | null;
  error: string | null;
}

/**
 * Client-Side Recursive AST Numerical Evaluator
 * Safely evaluates canonical ExprNode trees with live variable probe values,
 * catching singularities (division by zero, negative sqrt, log non-positive) and numerical overflows.
 */
export function evaluateAstNumeric(
  node: ExprNode | null | undefined,
  scope: Record<string, number> = {}
): EvaluationResult {
  if (!node) {
    return { value: null, error: "Empty or incomplete expression" };
  }

  try {
    switch (node.node_type) {
      case "constant": {
        const raw = node.value;
        const num = typeof raw === "number" ? raw : parseFloat(String(raw));
        if (isNaN(num)) {
          return { value: null, error: `Invalid constant value: ${raw}` };
        }
        return { value: num, error: null };
      }

      case "variable": {
        const symbol = String(node.value || "").trim();
        if (!symbol) {
          return { value: null, error: "Variable missing symbol declaration" };
        }
        if (symbol in scope && typeof scope[symbol] === "number" && !isNaN(scope[symbol])) {
          return { value: scope[symbol], error: null };
        }
        return {
          value: null,
          error: `Variable '${symbol}' has no assigned numerical value`,
        };
      }

      case "binary_op": {
        if (!node.left || !node.right) {
          return { value: null, error: `Binary operator '${node.op}' requires two operands` };
        }

        const leftRes = evaluateAstNumeric(node.left, scope);
        if (leftRes.error !== null || leftRes.value === null) {
          return leftRes;
        }

        const rightRes = evaluateAstNumeric(node.right, scope);
        if (rightRes.error !== null || rightRes.value === null) {
          return rightRes;
        }

        const l = leftRes.value;
        const r = rightRes.value;

        switch (node.op) {
          case "+":
            return { value: l + r, error: null };
          case "-":
            return { value: l - r, error: null };
          case "*":
            return { value: l * r, error: null };
          case "/": {
            if (Math.abs(r) < 1e-15) {
              return { value: null, error: "Singularity: division by zero" };
            }
            return { value: l / r, error: null };
          }
          case "**": {
            if (l < 0 && !Number.isInteger(r)) {
              return {
                value: null,
                error: "Domain error: negative base with non-integer exponent",
              };
            }
            const res = Math.pow(l, r);
            if (isNaN(res) || !isFinite(res)) {
              return { value: null, error: "Numerical overflow in exponentiation" };
            }
            return { value: res, error: null };
          }
          default:
            return { value: null, error: `Unsupported binary operator '${node.op}'` };
        }
      }

      case "unary_op": {
        const operand = node.left;
        if (!operand) {
          return { value: null, error: "Unary operator requires an operand" };
        }

        const childRes = evaluateAstNumeric(operand, scope);
        if (childRes.error !== null || childRes.value === null) {
          return childRes;
        }

        if (node.op === "neg" || node.op === "-") {
          return { value: -childRes.value, error: null };
        }

        return { value: null, error: `Unsupported unary operator '${node.op}'` };
      }

      case "function_call": {
        if (!node.args || node.args.length === 0) {
          return { value: null, error: `Function '${node.func}' requires arguments` };
        }

        const argRes = evaluateAstNumeric(node.args[0], scope);
        if (argRes.error !== null || argRes.value === null) {
          return argRes;
        }

        const val = argRes.value;

        switch (node.func) {
          case "sqrt": {
            if (val < 0) {
              return { value: null, error: "Domain error: square root of negative number" };
            }
            return { value: Math.sqrt(val), error: null };
          }
          case "sin":
            return { value: Math.sin(val), error: null };
          case "cos":
            return { value: Math.cos(val), error: null };
          case "exp": {
            const expVal = Math.exp(val);
            if (!isFinite(expVal)) {
              return { value: null, error: "Numerical overflow in exp()" };
            }
            return { value: expVal, error: null };
          }
          case "log": {
            if (val <= 0) {
              return { value: null, error: "Domain error: logarithm of non-positive number" };
            }
            return { value: Math.log(val), error: null };
          }
          default:
            return { value: null, error: `Unsupported function '${node.func}'` };
        }
      }

      default:
        return {
          value: null,
          error: `Unknown AST node type '${(node as { node_type?: string }).node_type}'`,
        };
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { value: null, error: msg };
  }
}

/**
 * Format numerical results cleanly for real-time telemetry chips
 */
export function formatEvaluatedValue(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) {
    return "—";
  }
  if (!isFinite(val)) {
    return val > 0 ? "+∞" : "-∞";
  }
  const abs = Math.abs(val);
  if (abs >= 1e6 || (abs < 1e-4 && abs !== 0)) {
    return val.toExponential(4);
  }
  return parseFloat(val.toFixed(4)).toString();
}
