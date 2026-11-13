import { ExprNode } from "@/types/contracts";

export function exprNodeToLatex(node: ExprNode): string {
  if (node.node_type === "constant") {
    return String(node.value ?? "");
  }
  if (node.node_type === "variable") {
    return String(node.value ?? "");
  }
  if (node.node_type === "unary_op" && node.left) {
    return `-${exprNodeToLatex(node.left)}`;
  }
  if (node.node_type === "binary_op" && node.left && node.right) {
    const leftStr = exprNodeToLatex(node.left);
    const rightStr = exprNodeToLatex(node.right);
    if (node.op === "/") {
      return `\\frac{${leftStr}}{${rightStr}}`;
    }
    if (node.op === "**") {
      return `{${leftStr}}^{${rightStr}}`;
    }
    if (node.op === "*") {
      return `${leftStr} \\cdot ${rightStr}`;
    }
    return `${leftStr} ${node.op} ${rightStr}`;
  }
  if (node.node_type === "function_call" && node.args && node.args.length > 0) {
    const argStr = exprNodeToLatex(node.args[0]);
    if (node.func === "sqrt") {
      return `\\sqrt{${argStr}}`;
    }
    return `\\${node.func}(${argStr})`;
  }
  return "";
}
