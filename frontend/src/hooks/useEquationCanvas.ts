"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { addEdge, applyEdgeChanges, applyNodeChanges, type Connection, type OnEdgesChange, type OnNodesChange } from "@xyflow/react";
import type { MathCanvasEdge, MathCanvasNode } from "@/types/canvas";
import type { ExprNode, FindingResult, VariableSpec, UnitSpec } from "@/types/contracts";
import type { NodeTypeToAdd } from "@/components/equations/canvas/CanvasToolbar";
import { astToGraph, graphToAst } from "@/lib/ast_graph_converter";
import { exprNodeToLatex } from "@/lib/ast";
import { evaluateAstNumeric, type EvaluationResult } from "@/lib/formula_evaluator";
import { validateEquationAst } from "@/lib/api";

export interface CanvasState {
  nodes: MathCanvasNode[];
  edges: MathCanvasEdge[];
  variables: VariableSpec[];
  units: UnitSpec[];
}

const emptyCalculation: EvaluationResult = { value: null, error: null };

function previewCanvas({ nodes, edges, variables }: CanvasState) {
  try {
    if (!nodes.length && !edges.length) {
      return { ast: null, latex: "", calculation: emptyCalculation, error: null };
    }
    const ast = graphToAst(nodes, edges, variables);
    return { ast, latex: exprNodeToLatex(ast), calculation: evaluateAstNumeric(ast, {}), error: null };
  } catch (cause) {
    return {
      ast: null, latex: "", calculation: emptyCalculation,
      error: cause instanceof Error ? cause.message : "The current canvas could not be computed.",
    };
  }
}

function layoutNodes(canvas: CanvasState): MathCanvasNode[] {
  // Check the graph, then move its existing nodes without rebuilding the DAG.
  graphToAst(canvas.nodes, canvas.edges, canvas.variables);
  const inputs = new Map<string, string[]>();
  for (const edge of canvas.edges) {
    const sources = inputs.get(edge.target) ?? [];
    sources.push(edge.source);
    inputs.set(edge.target, sources);
  }
  const positions = new Map<string, { level: number; y: number }>();
  const nextYByLevel = new Map<number, number>();
  function positionFor(id: string): { level: number; y: number } {
    const existing = positions.get(id);
    if (existing) return existing;
    const operands = (inputs.get(id) ?? []).map(positionFor);
    const level = operands.length ? Math.max(...operands.map((item) => item.level)) + 1 : 0;
    const preferredY = operands.length ? operands.reduce((sum, item) => sum + item.y, 0) / operands.length : 60;
    const y = Math.max(preferredY, nextYByLevel.get(level) ?? 60);
    const position = { level, y };
    positions.set(id, position);
    nextYByLevel.set(level, y + 110);
    return position;
  }
  return canvas.nodes.map((node) => {
    const position = positionFor(node.id);
    return { ...node, position: { x: 50 + position.level * 240, y: position.y } };
  });
}

export function useEquationCanvas() {
  const [canvas, setCanvas] = useState<CanvasState>({ nodes: [], edges: [], variables: [], units: [] });
  const latestCanvas = useRef(canvas);
  const [validationResult, setValidationResult] = useState<FindingResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const requestId = useRef(0);
  const nodeSequence = useRef(100);

  // Event/effect-only gateway: queued edits and validation share the latest snapshot.
  // The transform is pure; no state updater or render mutates this ref.
  const updateCanvas = useCallback((transform: (previous: CanvasState) => CanvasState) => {
    const next = transform(latestCanvas.current);
    latestCanvas.current = next;
    setCanvas(next);
  }, []);

  // Called only by events/effects, never from a state updater or render.
  const invalidateValidation = useCallback(() => {
    requestId.current += 1;
    setValidationResult(null);
    setIsValidating(false);
    setActionError(null);
  }, []);

  const cancelPendingValidation = useCallback(() => {
    requestId.current += 1;
  }, []);

  const replaceCanvas = useCallback((ast: ExprNode | null, variables: VariableSpec[], units: UnitSpec[] = []) => {
    const graph = ast ? astToGraph(ast, variables) : { nodes: [], edges: [] };
    invalidateValidation();
    updateCanvas(() => ({ ...graph, edges: graph.edges.map((edge) => ({ ...edge, type: "pulseFlow" })), variables, units }));
  }, [invalidateValidation, updateCanvas]);

  const getCanvasSnapshot = useCallback(() => latestCanvas.current, []);
  const restoreCanvas = useCallback((snapshot: CanvasState) => {
    invalidateValidation();
    updateCanvas(() => snapshot);
  }, [invalidateValidation, updateCanvas]);

  const handleVariablesChange = useCallback((variables: VariableSpec[]) => {
    invalidateValidation();
    updateCanvas((previous) => ({ ...previous, variables }));
  }, [invalidateValidation, updateCanvas]);

  const handleUnitsChange = useCallback((units: UnitSpec[]) => {
    invalidateValidation();
    updateCanvas((previous) => ({ ...previous, units }));
  }, [invalidateValidation, updateCanvas]);

  const getSaveSnapshot = useCallback(() => {
    const snapshot = latestCanvas.current;
    const preview = previewCanvas(snapshot);
    if (preview.error) throw new Error(preview.error);
    return { ast: preview.ast, latex: preview.latex, variables: snapshot.variables, units: snapshot.units };
  }, []);

  const onNodesChange: OnNodesChange<MathCanvasNode> = useCallback((changes) => {
    if (changes.some((change) => ["add", "remove", "replace"].includes(change.type))) invalidateValidation();
    updateCanvas((previous) => ({ ...previous, nodes: applyNodeChanges(changes, previous.nodes) }));
  }, [invalidateValidation, updateCanvas]);

  const onEdgesChange: OnEdgesChange<MathCanvasEdge> = useCallback((changes) => {
    if (changes.some((change) => change.type !== "select")) invalidateValidation();
    updateCanvas((previous) => ({ ...previous, edges: applyEdgeChanges(changes, previous.edges) }));
  }, [invalidateValidation, updateCanvas]);

  const onConnect = useCallback((connection: Connection) => {
    invalidateValidation();
    updateCanvas((previous) => ({
      ...previous,
      edges: addEdge({ ...connection, type: "pulseFlow", animated: true }, previous.edges),
    }));
  }, [invalidateValidation, updateCanvas]);

  const handleNodeDataChange = useCallback((nodeId: string, data: Record<string, unknown>) => {
    invalidateValidation();
    updateCanvas((previous) => ({
      ...previous,
      nodes: previous.nodes.map((node) => node.id === nodeId ? { ...node, data: { ...node.data, ...data } } as MathCanvasNode : node),
    }));
  }, [invalidateValidation, updateCanvas]);

  const handleAddNode = useCallback((type: NodeTypeToAdd) => {
    invalidateValidation();
    // Allocate once per event, outside the pure transform.
    const id = `draft_${++nodeSequence.current}`;
    updateCanvas((previous) => {
      const position = { x: 120 + (previous.nodes.length % 5) * 40, y: 140 + (previous.nodes.length % 5) * 40 };
      let node: MathCanvasNode;
      switch (type) {
        case "constant": node = { id, position, type: "constantNode", data: { value: 1 } }; break;
        case "variable": node = { id, position, type: "variableNode", data: { symbol: previous.variables[0]?.symbol || "v" } }; break;
        case "binary_op": node = { id, position, type: "binaryOpNode", data: { op: "+" } }; break;
        case "unary_op": node = { id, position, type: "unaryOpNode", data: { op: "neg" } }; break;
        case "function_call": node = { id, position, type: "functionCallNode", data: { func: "sqrt" } }; break;
        case "equation_root": node = { id, position, type: "equationRootNode", data: { name: "R" } }; break;
      }
      return { ...previous, nodes: [...previous.nodes, node] };
    });
  }, [invalidateValidation, updateCanvas]);

  const handleAutoLayout = useCallback(() => {
    setActionError(null);
    updateCanvas((previous) => {
      try {
        return { ...previous, nodes: layoutNodes(previous) };
      } catch {
        // Preserve invalid input; the derived preview reports its diagnostic.
        return previous;
      }
    });
  }, [updateCanvas]);

  const handleClear = useCallback(() => {
    if (window.confirm("Are you sure you want to clear the entire canvas?")) {
      invalidateValidation();
      updateCanvas((previous) => ({ ...previous, nodes: [], edges: [] }));
    }
  }, [invalidateValidation, updateCanvas]);

  const handleValidate = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setValidationResult(null);
    setActionError(null);
    setIsValidating(true);
    try {
      const snapshot = latestCanvas.current;
      const ast = graphToAst(snapshot.nodes, snapshot.edges, snapshot.variables);
      const finding = await validateEquationAst({ expression_ast: ast, variables: snapshot.variables,
        ...(snapshot.units.length ? { units: snapshot.units } : {}) });
      if (currentRequest === requestId.current) setValidationResult(finding);
    } catch (cause) {
      if (currentRequest === requestId.current) {
        setActionError(cause instanceof Error ? cause.message : "Validation failed");
      }
    } finally {
      if (currentRequest === requestId.current) setIsValidating(false);
    }
  }, []);

  // Derive every preview from the same snapshot; never write derived values back to state.
  const preview = useMemo(() => previewCanvas(canvas), [canvas]);
  const nodes = useMemo(() => canvas.nodes.map((node) => node.type === "equationRootNode"
    ? { ...node, data: { ...node.data, latex: preview.latex, computedValue: preview.calculation.value ?? undefined } }
    : node), [canvas.nodes, preview]);

  return {
    nodes, edges: canvas.edges, variables: canvas.variables, units: canvas.units,
    currentAst: preview.ast, currentLatex: preview.latex, computedResult: preview.calculation,
    translationError: preview.error ?? actionError, validationResult, isValidating,
    replaceCanvas, restoreCanvas, getCanvasSnapshot, cancelPendingValidation, handleVariablesChange, handleNodeDataChange, handleUnitsChange, getSaveSnapshot,
    onNodesChange, onEdgesChange, onConnect, handleAddNode, handleAutoLayout, handleClear, handleValidate,
  };
}
