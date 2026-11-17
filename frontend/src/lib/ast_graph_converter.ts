import { ExprNode, VariableSpec, OperatorType, AllowedFunction } from "@/types/contracts";
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
import { exprNodeToLatex } from "@/lib/ast";

export class TranslationError extends Error {
  public nodeId?: string;

  constructor(message: string, nodeId?: string) {
    super(message);
    this.name = "TranslationError";
    this.nodeId = nodeId;
  }
}

const MAX_AST_DEPTH = 15;
const MAX_AST_NODES = 100;

export function assertCanonicalAst(value: unknown): asserts value is ExprNode {
  let nodeCount = 0;

  function visit(node: unknown, depth: number): asserts node is ExprNode {
    if (!node || typeof node !== "object" || Array.isArray(node)) {
      throw new TranslationError("Stored equation contains an invalid AST node.");
    }
    if (depth > MAX_AST_DEPTH) {
      throw new TranslationError(`AST recursion depth exceeded guardrail limit (max ${MAX_AST_DEPTH}).`);
    }
    nodeCount += 1;
    if (nodeCount > MAX_AST_NODES) {
      throw new TranslationError(`AST node count exceeded guardrail limit (max ${MAX_AST_NODES}).`);
    }

    const candidate = node as Record<string, unknown>;
    switch (candidate.node_type) {
      case "constant": {
        const numericValue = typeof candidate.value === "number"
          ? candidate.value
          : typeof candidate.value === "string" && candidate.value.trim() !== ""
            ? Number(candidate.value)
            : Number.NaN;
        if (!Number.isFinite(numericValue)) {
          throw new TranslationError("Stored equation contains an invalid constant.");
        }
        return;
      }
      case "variable":
        if (typeof candidate.value !== "string" || !candidate.value.trim()) {
          throw new TranslationError("Stored equation contains a variable without a symbol.");
        }
        return;
      case "unary_op":
        if (candidate.op !== "neg") {
          throw new TranslationError("Stored equation contains an unsupported unary operator.");
        }
        visit(candidate.left, depth + 1);
        return;
      case "binary_op":
        if (!["+", "-", "*", "/", "**"].includes(String(candidate.op))) {
          throw new TranslationError("Stored equation contains an unsupported binary operator.");
        }
        visit(candidate.left, depth + 1);
        visit(candidate.right, depth + 1);
        return;
      case "function_call":
        if (!["sqrt", "sin", "cos", "exp", "log"].includes(String(candidate.func))) {
          throw new TranslationError("Stored equation contains an unsupported function.");
        }
        if (!Array.isArray(candidate.args) || candidate.args.length !== 1) {
          throw new TranslationError("Stored equation contains an invalid function argument list.");
        }
        visit(candidate.args[0], depth + 1);
        return;
      default:
        throw new TranslationError("Stored equation contains an unknown AST node type.");
    }
  }

  visit(value, 1);
}

/**
 * Traverses a canvas DAG and converts it into a canonical ExprNode JSON tree.
 * Enforces cycle detection, depth limits (<= 15), total node limits (<= 100),
 * variable declarations and every node/edge in the single-expression canvas.
 * Shared operands are expanded into the AST tree and count toward its limits.
 */
export function graphToAst(
  nodes: MathCanvasNode[],
  edges: MathCanvasEdge[],
  declaredVariables: VariableSpec[] = []
): ExprNode {
  if (!nodes || nodes.length === 0) {
    throw new TranslationError("Canvas has no nodes to evaluate.");
  }

  const declaredSymbols = new Set(declaredVariables.map((v) => v.symbol));
  const nodeMap = new Map<string, MathCanvasNode>();
  const incomingEdges = new Map<string, Map<string, MathCanvasEdge>>();
  const ports: Record<string, string[]> = {
    constantNode: [], variableNode: [], binaryOpNode: ["left", "right"],
    unaryOpNode: ["left"], functionCallNode: ["arg0"], equationRootNode: ["input"],
  };
  for (const node of nodes) {
    if (nodeMap.has(node.id)) throw new TranslationError(`Duplicate node ID '${node.id}'.`, node.id);
    if (!node.type || !Object.hasOwn(ports, node.type)) {
      throw new TranslationError(`Unknown node type: ${node.type ?? "unknown"}`, node.id);
    }
    nodeMap.set(node.id, node);
    incomingEdges.set(node.id, new Map());
  }

  const edgeIds = new Set<string>();
  for (const edge of edges) {
    if (edgeIds.has(edge.id)) throw new TranslationError(`Duplicate edge ID '${edge.id}'.`, edge.target);
    edgeIds.add(edge.id);
    const source = nodeMap.get(edge.source);
    const target = nodeMap.get(edge.target);
    if (!source || !target) {
      const missingId = !source ? edge.source : edge.target;
      throw new TranslationError(`Edge '${edge.id}' references missing node '${missingId}'.`, missingId);
    }
    if (source.type === "equationRootNode") {
      throw new TranslationError(`Equation root '${source.id}' has no output port.`, source.id);
    }
    if (edge.sourceHandle != null && edge.sourceHandle !== "output") {
      throw new TranslationError(`Invalid source port '${edge.sourceHandle}' on node '${source.id}'.`, source.id);
    }
    const allowed = ports[target.type!];
    if (allowed.length === 0) {
      throw new TranslationError(`Node '${target.id}' has no input port.`, target.id);
    }
    // Older graphs may omit the sole handle; a binary input is never inferred.
    const port = edge.targetHandle ?? (allowed.length === 1 ? allowed[0] : "");
    if (!allowed.includes(port)) {
      throw new TranslationError(`Invalid target port '${edge.targetHandle ?? "unspecified"}' on node '${target.id}'.`, target.id);
    }
    const inputs = incomingEdges.get(target.id)!;
    if (inputs.has(port)) {
      throw new TranslationError(`Multiple edges connect to input '${port}' on node '${target.id}'. Keep one operand per input.`, target.id);
    }
    inputs.set(port, edge);
  }

  // An explicit root is optional, but every canvas must have exactly one sink.
  const outgoingSourceIds = new Set(edges.map((e) => e.source));
  const equationRootNodes = nodes.filter((n) => n.type === "equationRootNode");

  let rootNode: MathCanvasNode;
  if (equationRootNodes.length > 1) {
    throw new TranslationError("Multiple equation roots found. This canvas supports one expression; remove extra roots.", equationRootNodes[1].id);
  }
  if (equationRootNodes.length === 1) {
    rootNode = equationRootNodes[0];
  } else {
    const candidateRoots = nodes.filter((n) => !outgoingSourceIds.has(n.id));
    if (candidateRoots.length === 0) {
      throw new TranslationError(
        "Cyclic graph detected. Mathematical AST must be a directed acyclic tree."
      );
    }
    if (candidateRoots.length > 1) {
      throw new TranslationError("Multiple expression roots found. Connect all nodes into one expression.", candidateRoots[1].id);
    }
    rootNode = candidateRoots[0];
  }

  // An isolated cycle has no sink, so root counting alone cannot detect it.
  const reachable = new Set<string>();
  const pending = [rootNode.id];
  while (pending.length) {
    const id = pending.pop()!;
    if (reachable.has(id)) continue;
    reachable.add(id);
    for (const edge of incomingEdges.get(id)!.values()) pending.push(edge.source);
  }
  const disconnected = nodes.find((node) => !reachable.has(node.id));
  if (disconnected) {
    throw new TranslationError(`Disconnected node '${disconnected.id}' is outside the expression. Connect or remove it before validation.`, disconnected.id);
  }

  const visitedOnPath = new Set<string>();
  let totalTraversedNodes = 0;

  function traverse(nodeId: string, depth: number): ExprNode {
    if (depth > MAX_AST_DEPTH) {
      throw new TranslationError(
        `AST recursion depth exceeded guardrail limit (max ${MAX_AST_DEPTH}).`,
        nodeId
      );
    }

    if (visitedOnPath.has(nodeId)) {
      throw new TranslationError(
        "Cyclic graph detected. Mathematical AST must be a directed acyclic tree.",
        nodeId
      );
    }

    const node = nodeMap.get(nodeId)!;
    // The visual result node is not a canonical AST node.
    if (node.type !== "equationRootNode") totalTraversedNodes += 1;
    if (totalTraversedNodes > MAX_AST_NODES) {
      throw new TranslationError(
        `AST node count exceeded guardrail limit (max ${MAX_AST_NODES}).`,
        nodeId
      );
    }

    visitedOnPath.add(nodeId);

    try {
      // Equation Root Node (sink node)
      if (node.type === "equationRootNode") {
        const incoming = incomingEdges.get(nodeId)!.get("input");
        if (!incoming) {
          throw new TranslationError(
            "Root node is not connected to an expression.",
            nodeId
          );
        }
        return traverse(incoming.source, depth);
      }

      // Constant Node (leaf)
      if (node.type === "constantNode") {
        const raw = node.data?.value;
        if (raw === undefined || raw === null || (typeof raw === "string" && raw.trim() === "")) {
          throw new TranslationError("Constant node is missing a value.", nodeId);
        }
        const num = Number(raw);
        if (isNaN(num) || !isFinite(num)) {
          throw new TranslationError(
            `Invalid constant value: '${raw}' is not a finite number.`,
            nodeId
          );
        }
        return {
          node_type: "constant",
          // Numeric strings may carry precision beyond JavaScript's Number.
          value: raw,
        };
      }

      // Variable Node (leaf)
      if (node.type === "variableNode") {
        const sym = String(node.data?.symbol ?? "").trim();
        if (!sym) {
          throw new TranslationError(
            "Variable node has no symbol selected.",
            nodeId
          );
        }
        if (!declaredSymbols.has(sym)) {
          throw new TranslationError(
            `Symbol '${sym}' is undeclared. Declare it in Variable Table first.`,
            nodeId
          );
        }
        return {
          node_type: "variable",
          value: sym,
        };
      }

      // Unary Operator Node
      if (node.type === "unaryOpNode") {
        if (node.data.op !== "neg") throw new TranslationError("Unsupported unary operator.", nodeId);
        const incoming = incomingEdges.get(nodeId)!.get("left");
        if (!incoming) {
          throw new TranslationError(
            "Unary operator node is missing operand.",
            nodeId
          );
        }
        return {
          node_type: "unary_op",
          op: "neg",
          left: traverse(incoming.source, depth + 1),
        };
      }

      // Binary Operator Node
      if (node.type === "binaryOpNode") {
        const op = node.data.op as OperatorType;
        if (!["+", "-", "*", "/", "**"].includes(op)) throw new TranslationError("Unsupported binary operator.", nodeId);
        const leftEdge = incomingEdges.get(nodeId)!.get("left");
        const rightEdge = incomingEdges.get(nodeId)!.get("right");

        if (!leftEdge) {
          throw new TranslationError(
            `Binary operator '${op}' missing left operand.`,
            nodeId
          );
        }
        if (!rightEdge) {
          throw new TranslationError(
            `Binary operator '${op}' missing right operand.`,
            nodeId
          );
        }

        return {
          node_type: "binary_op",
          op,
          left: traverse(leftEdge.source, depth + 1),
          right: traverse(rightEdge.source, depth + 1),
        };
      }

      // Function Call Node
      if (node.type === "functionCallNode") {
        const func = node.data.func as AllowedFunction;
        if (!["sqrt", "sin", "cos", "exp", "log"].includes(func)) throw new TranslationError("Unsupported function.", nodeId);
        const argEdge = incomingEdges.get(nodeId)!.get("arg0");

        if (!argEdge) {
          throw new TranslationError(
            `Function call node '${func}' missing argument.`,
            nodeId
          );
        }

        return {
          node_type: "function_call",
          func,
          args: [traverse(argEdge.source, depth + 1)],
        };
      }

      const unknownType = (node as { type?: string })?.type ?? "unknown";
      throw new TranslationError(`Unknown node type: ${unknownType}`, nodeId);
    } finally {
      visitedOnPath.delete(nodeId);
    }
  }

  return traverse(rootNode.id, 1);
}

/**
 * Converts a canonical ExprNode JSON tree into a set of visual @xyflow/react
 * nodes and directed edges arranged with left-to-right hierarchical coordinates.
 */
export function astToGraph(
  ast: ExprNode,
  declaredVariables: VariableSpec[] = []
): { nodes: MathCanvasNode[]; edges: MathCanvasEdge[] } {
  const nodes: MathCanvasNode[] = [];
  const edges: MathCanvasEdge[] = [];

  const declaredMap = new Map(declaredVariables.map((v) => [v.symbol, v]));
  let idCounter = 1;
  let nextLeafY = 60;
  const Y_SPACING = 110;
  const X_SPACING = 240;

  function buildGraph(expr: ExprNode): { id: string; xLevel: number; y: number } {
    const id = `node_${idCounter++}`;

    if (expr.node_type === "constant") {
      const y = nextLeafY;
      nextLeafY += Y_SPACING;
      const node: ConstantNode = {
        id,
        type: "constantNode",
        position: { x: 0, y }, // X calculated after tree levels determined
        data: {
          value: expr.value ?? 0,
        },
      };
      nodes.push(node);
      return { id, xLevel: 0, y };
    }

    if (expr.node_type === "variable") {
      const sym = String(expr.value ?? "");
      const varSpec = declaredMap.get(sym);
      const y = nextLeafY;
      nextLeafY += Y_SPACING;
      const node: VariableNode = {
        id,
        type: "variableNode",
        position: { x: 0, y },
        data: {
          symbol: sym,
          name: varSpec?.name,
          unit: varSpec?.unit,
        },
      };
      nodes.push(node);
      return { id, xLevel: 0, y };
    }

    if (expr.node_type === "unary_op" && expr.left) {
      const child = buildGraph(expr.left);
      const xLevel = child.xLevel + 1;
      const y = child.y;

      const node: UnaryOpNode = {
        id,
        type: "unaryOpNode",
        position: { x: 0, y },
        data: {
          op: "neg",
        },
      };
      nodes.push(node);

      edges.push({
        id: `e_${child.id}_to_${id}`,
        source: child.id,
        sourceHandle: "output",
        target: id,
        targetHandle: "left",
        type: "pulseFlowEdge",
        animated: true,
      });

      return { id, xLevel, y };
    }

    if (expr.node_type === "binary_op" && expr.left && expr.right) {
      const leftChild = buildGraph(expr.left);
      const rightChild = buildGraph(expr.right);
      const xLevel = Math.max(leftChild.xLevel, rightChild.xLevel) + 1;
      const y = (leftChild.y + rightChild.y) / 2;

      const node: BinaryOpNode = {
        id,
        type: "binaryOpNode",
        position: { x: 0, y },
        data: {
          op: expr.op ?? "+",
        },
      };
      nodes.push(node);

      edges.push({
        id: `e_${leftChild.id}_to_${id}_l`,
        source: leftChild.id,
        sourceHandle: "output",
        target: id,
        targetHandle: "left",
        type: "pulseFlowEdge",
        animated: true,
      });

      edges.push({
        id: `e_${rightChild.id}_to_${id}_r`,
        source: rightChild.id,
        sourceHandle: "output",
        target: id,
        targetHandle: "right",
        type: "pulseFlowEdge",
        animated: true,
      });

      return { id, xLevel, y };
    }

    if (expr.node_type === "function_call" && expr.args && expr.args.length > 0) {
      const child = buildGraph(expr.args[0]);
      const xLevel = child.xLevel + 1;
      const y = child.y;

      const node: FunctionCallNode = {
        id,
        type: "functionCallNode",
        position: { x: 0, y },
        data: {
          func: expr.func ?? "sqrt",
        },
      };
      nodes.push(node);

      edges.push({
        id: `e_${child.id}_to_${id}_arg`,
        source: child.id,
        sourceHandle: "output",
        target: id,
        targetHandle: "arg0",
        type: "pulseFlowEdge",
        animated: true,
      });

      return { id, xLevel, y };
    }

    // Fallback: Constant node for unexpected leaf
    const y = nextLeafY;
    nextLeafY += Y_SPACING;
    const fallbackNode: ConstantNode = {
      id,
      type: "constantNode",
      position: { x: 0, y },
      data: { value: 0 },
    };
    nodes.push(fallbackNode);
    return { id, xLevel: 0, y };
  }

  const topLevel = buildGraph(ast);

  // Position X based on hierarchy level
  // Also track max level for EquationRootNode
  let maxLevel = 0;
  // Node level map from building
  // We can update positions:
  // First, map nodes by ID to their level
  // Since buildGraph returned xLevel, we can adjust all nodes:
  // We will re-scan node hierarchy or store xLevel in map:
  // Let's create level map:
  const levelMap = new Map<string, number>();

  // To ensure correct positioning, we can do a topological level computation
  // or simply record level during creation:
  // Let's record level during creation by storing on a temporary map:
  function getDepthMap() {
    const depths = new Map<string, number>();
    // leaves have indegree 0 in reverse dataflow
    const incomingEdges = new Map<string, string[]>();
    for (const e of edges) {
      if (!incomingEdges.has(e.target)) incomingEdges.set(e.target, []);
      incomingEdges.get(e.target)!.push(e.source);
    }

    function computeLevel(nodeId: string): number {
      if (depths.has(nodeId)) return depths.get(nodeId)!;
      const sources = incomingEdges.get(nodeId) || [];
      if (sources.length === 0) {
        depths.set(nodeId, 0);
        return 0;
      }
      const maxChildLevel = Math.max(...sources.map(computeLevel));
      const myLevel = maxChildLevel + 1;
      depths.set(nodeId, myLevel);
      return myLevel;
    }

    for (const n of nodes) {
      computeLevel(n.id);
    }
    return depths;
  }

  const depthMap = getDepthMap();
  for (const n of nodes) {
    const lvl = depthMap.get(n.id) ?? 0;
    n.position.x = 50 + lvl * X_SPACING;
    if (lvl > maxLevel) maxLevel = lvl;
  }

  // Finally, attach the EquationRootNode as the ultimate sink
  const rootId = `root_${idCounter++}`;
  const rootNode: EquationRootNode = {
    id: rootId,
    type: "equationRootNode",
    position: {
      x: 50 + (maxLevel + 1) * X_SPACING,
      y: topLevel.y,
    },
    data: {
      name: "R",
      latex: exprNodeToLatex(ast),
    },
  };
  nodes.push(rootNode);

  edges.push({
    id: `e_${topLevel.id}_to_${rootId}`,
    source: topLevel.id,
    sourceHandle: "output",
    target: rootId,
    targetHandle: "input",
    type: "pulseFlowEdge",
    animated: true,
  });

  return { nodes, edges };
}
