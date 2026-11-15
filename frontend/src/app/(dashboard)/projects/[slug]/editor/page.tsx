"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Connection,
  type OnNodesChange,
  type OnEdgesChange,
} from "@xyflow/react";

import { VariableSpec, ExprNode, FindingResult } from "@/types/contracts";
import { MathCanvasNode, MathCanvasEdge } from "@/types/canvas";
import { graphToAst, astToGraph, TranslationError } from "@/lib/ast_graph_converter";
import { exprNodeToLatex } from "@/lib/ast";
import { validateEquationAst } from "@/lib/api";
import { evaluateAstNumeric, formatEvaluatedValue, type EvaluationResult } from "@/lib/formula_evaluator";

import { SymbolicCanvas } from "@/components/equations/canvas/SymbolicCanvas";
import { NodeTypeToAdd } from "@/components/equations/canvas/CanvasToolbar";
import {
  ScientificPresetsBar,
  CANONICAL_PRESETS,
  type ScientificPreset,
} from "@/components/equations/canvas/ScientificPresetsBar";
import { VariableDeclarationPanel } from "@/components/equations/VariableDeclarationPanel";
import { ValidationStatusBar } from "@/components/equations/ValidationStatusBar";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { AstVisualizer } from "@/components/equations/AstVisualizer";
import { Card } from "@/components/ui/Card";
import { Code2, Sparkles, Layers, Activity, Calculator } from "lucide-react";

// Default physical variables for demonstration: v = a * t
const INITIAL_VARIABLES: VariableSpec[] = [
  {
    symbol: "v",
    name: "Velocity",
    unit: "meter / second",
    domain: "real",
    latex_presentation: "v",
  },
  {
    symbol: "a",
    name: "Acceleration",
    unit: "meter / second ** 2",
    domain: "real",
    latex_presentation: "a",
  },
  {
    symbol: "t",
    name: "Time",
    unit: "second",
    domain: "positive_real",
    latex_presentation: "t",
  },
];

// Initial AST: a * t
const INITIAL_AST: ExprNode = {
  node_type: "binary_op",
  op: "*",
  left: { node_type: "variable", value: "a" },
  right: { node_type: "variable", value: "t" },
};

// Initial physical probe values for real-time telemetry calculation
const DEFAULT_PROBE_SCOPE: Record<string, number> = {
  v: 39.4,
  v_0: 10,
  a: 9.8,
  t: 3,
  m: 2,
  c: 299792458,
  G: 6.674e-11,
  M: 5.972e24,
  r: 6371000,
  x: 5,
  y: 10,
  k: 1,
};

export default function EquationEditorPage({
  params: _params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const params = useParams();
  const slug = (params?.slug as string) || "default-model";

  const [variables, setVariables] = useState<VariableSpec[]>(INITIAL_VARIABLES);
  const [nodes, setNodes] = useState<MathCanvasNode[]>([]);
  const [edges, setEdges] = useState<MathCanvasEdge[]>([]);
  const [currentAst, setCurrentAst] = useState<ExprNode | null>(INITIAL_AST);
  const [currentLatex, setCurrentLatex] = useState<string>("a \\cdot t");
  const [probeScope] = useState<Record<string, number>>(DEFAULT_PROBE_SCOPE);
  const [computedResult, setComputedResult] = useState<EvaluationResult>({
    value: 29.4,
    error: null,
  });
  const [validationResult, setValidationResult] = useState<FindingResult | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [nodeIdCounter, setNodeIdCounter] = useState<number>(100);

  // Quick-Load Preset Handler
  const handleSelectPreset = useCallback(async (preset: ScientificPreset) => {
    setTranslationError(null);

    // 1. Update variables state
    setVariables(preset.variables);

    // 2. Build graph from preset AST and variables
    const { nodes: newNodes, edges: newEdges } = astToGraph(preset.ast, preset.variables);
    const pulseEdges = newEdges.map((e) => ({ ...e, type: "pulseFlow" }));

    // 3. Compute live numerical evaluation
    const evalRes = evaluateAstNumeric(preset.ast, probeScope);
    setComputedResult(evalRes);

    const latex = preset.formulaLatex || exprNodeToLatex(preset.ast);
    setCurrentAst(preset.ast);
    setCurrentLatex(latex);

    // Enrich equation root node with computed preview
    const enrichedNodes = newNodes.map((n) =>
      n.type === "equationRootNode"
        ? { ...n, data: { ...n.data, latex, computedValue: evalRes.value } }
        : n
    );
    setNodes(enrichedNodes);
    setEdges(pulseEdges);

    // 4. Auto-trigger 6-layer scientific validation
    setIsValidating(true);
    try {
      const finding = await validateEquationAst({
        expression_ast: preset.ast,
        variables: preset.variables,
      });
      setValidationResult(finding);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Validation failed";
      setTranslationError(msg);
    } finally {
      setIsValidating(false);
    }
  }, [probeScope]);

  // Initialize canvas with initial AST layout or query parameter preset
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const presetParam = urlParams.get("preset");
      if (presetParam) {
        const found = CANONICAL_PRESETS.find(
          (p) => p.id === presetParam || p.id.toLowerCase().includes(presetParam.toLowerCase())
        );
        if (found) {
          handleSelectPreset(found);
          return;
        }
      }
    }

    const { nodes: initialNodes, edges: initialEdges } = astToGraph(INITIAL_AST, INITIAL_VARIABLES);
    const initialEval = evaluateAstNumeric(INITIAL_AST, DEFAULT_PROBE_SCOPE);
    setComputedResult(initialEval);

    const enriched = initialNodes.map((n) =>
      n.type === "equationRootNode"
        ? { ...n, data: { ...n.data, computedValue: initialEval.value } }
        : n
    );
    setNodes(enriched);
    setEdges(initialEdges.map((e) => ({ ...e, type: "pulseFlow" })));
  }, [handleSelectPreset]);

  // Compute set of symbols currently used on canvas
  const usedSymbols = useMemo(() => {
    const syms = new Set<string>();
    for (const node of nodes) {
      if (node.type === "variableNode" && node.data?.symbol) {
        syms.add(node.data.symbol);
      }
    }
    return syms;
  }, [nodes]);

  // Synchronize AST, live LaTeX, and formula evaluator when nodes or edges change
  const syncAst = useCallback(
    (currentNodes: MathCanvasNode[], currentEdges: MathCanvasEdge[]) => {
      try {
        const ast = graphToAst(currentNodes, currentEdges, variables);
        const latex = exprNodeToLatex(ast);
        setCurrentAst(ast);
        setCurrentLatex(latex);
        setTranslationError(null);

        // Live real-time numerical formula evaluation
        const evalRes = evaluateAstNumeric(ast, probeScope);
        setComputedResult(evalRes);

        // Update EquationRootNode with live LaTeX and computed value if present
        setNodes((prevNodes) =>
          prevNodes.map((n) =>
            n.type === "equationRootNode"
              ? { ...n, data: { ...n.data, latex, computedValue: evalRes.value } }
              : n
          )
        );
      } catch (err) {
        if (err instanceof TranslationError) {
          setTranslationError(err.message);
        }
      }
    },
    [variables, probeScope]
  );

  const onNodesChange: OnNodesChange<MathCanvasNode> = useCallback(
    (changes) => {
      setNodes((nds) => {
        const nextNodes = applyNodeChanges(changes, nds) as MathCanvasNode[];
        syncAst(nextNodes, edges);
        return nextNodes;
      });
    },
    [edges, syncAst]
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      setEdges((eds) => {
        const nextEdges = applyEdgeChanges(changes, eds) as MathCanvasEdge[];
        syncAst(nodes, nextEdges);
        return nextEdges;
      });
    },
    [nodes, syncAst]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => {
        const nextEdges = addEdge(
          {
            ...connection,
            type: "pulseFlow",
            animated: true,
            style: { stroke: "#0ea5e9", strokeWidth: 2 },
          },
          eds
        ) as MathCanvasEdge[];
        syncAst(nodes, nextEdges);
        return nextEdges;
      });
    },
    [nodes, syncAst]
  );

  const handleNodeDataChange = useCallback(
    (nodeId: string, updatedData: Record<string, unknown>) => {
      setNodes((prevNodes) => {
        const nextNodes = prevNodes.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...updatedData } } : n
        ) as MathCanvasNode[];
        syncAst(nextNodes, edges);
        return nextNodes;
      });
    },
    [edges, syncAst]
  );

  const handleAddNode = useCallback(
    (type: NodeTypeToAdd) => {
      const newId = `node_${nodeIdCounter + 1}`;
      setNodeIdCounter((c) => c + 1);

      // Position in viewport center or slightly staggered
      const x = 120 + (nodes.length % 5) * 40;
      const y = 140 + (nodes.length % 5) * 40;

      let newNode: MathCanvasNode;

      switch (type) {
        case "constant":
          newNode = {
            id: newId,
            type: "constantNode",
            position: { x, y },
            data: { value: 1 },
          };
          break;
        case "variable":
          newNode = {
            id: newId,
            type: "variableNode",
            position: { x, y },
            data: {
              symbol: variables[0]?.symbol || "v",
              name: variables[0]?.name,
              unit: variables[0]?.unit,
            },
          };
          break;
        case "binary_op":
          newNode = {
            id: newId,
            type: "binaryOpNode",
            position: { x, y },
            data: { op: "+" },
          };
          break;
        case "unary_op":
          newNode = {
            id: newId,
            type: "unaryOpNode",
            position: { x, y },
            data: { op: "neg" },
          };
          break;
        case "function_call":
          newNode = {
            id: newId,
            type: "functionCallNode",
            position: { x, y },
            data: { func: "sqrt" },
          };
          break;
        case "equation_root":
          newNode = {
            id: newId,
            type: "equationRootNode",
            position: { x, y },
            data: { name: "R", latex: currentLatex, computedValue: computedResult.value },
          };
          break;
      }

      setNodes((nds) => [...nds, newNode]);
    },
    [nodeIdCounter, nodes.length, variables, currentLatex, computedResult.value]
  );

  const handleAutoLayout = useCallback(() => {
    try {
      const ast = graphToAst(nodes, edges, variables);
      const { nodes: layoutNodes, edges: layoutEdges } = astToGraph(ast, variables);
      setNodes(layoutNodes);
      setEdges(layoutEdges.map((e) => ({ ...e, type: "pulseFlow" })));
      setTranslationError(null);
    } catch (err) {
      if (err instanceof TranslationError) {
        setTranslationError(`Cannot auto-layout: ${err.message}`);
      }
    }
  }, [nodes, edges, variables]);

  const handleClear = useCallback(() => {
    if (window.confirm("Are you sure you want to clear the entire canvas?")) {
      setNodes([]);
      setEdges([]);
      setCurrentAst(null);
      setCurrentLatex("");
      setComputedResult({ value: null, error: null });
      setValidationResult(null);
      setTranslationError(null);
    }
  }, []);

  const handleValidate = useCallback(async () => {
    setIsValidating(true);
    setTranslationError(null);

    try {
      // 1. Convert canvas to canonical AST
      const ast = graphToAst(nodes, edges, variables);
      setCurrentAst(ast);
      setCurrentLatex(exprNodeToLatex(ast));

      // 2. Dispatch to backend compute sandbox (or pre-flight fallback)
      const finding = await validateEquationAst({
        expression_ast: ast,
        variables,
      });

      setValidationResult(finding);
    } catch (err) {
      if (err instanceof TranslationError) {
        setTranslationError(err.message);
        setValidationResult({
          job_id: `err-${Date.now()}`,
          state: "FAIL",
          diagnostic_code: "AST_CONSTRUCTION_ERROR",
          message: err.message,
          dimensions_verified: false,
          diagnostics: [
            `Node '${err.nodeId || "canvas"}' triggered validation failure: ${err.message}`,
            "Inspect canvas port connections and declared symbols.",
          ],
        });
      } else {
        const errorMsg = (err as Error)?.message || "Unknown validation error";
        setTranslationError(errorMsg);
      }
    } finally {
      setIsValidating(false);
    }
  }, [nodes, edges, variables]);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">
            <Layers className="h-4 w-4" />
            <span>Interactive Symbolic Canvas Studio</span>
            <span className="flex items-center gap-1 text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 px-2 py-0.5 rounded-full font-mono shadow-sm">
              <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
              PulseFlow Active
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 mt-1">
            Mathematical Model Editor — {slug}
          </h1>
          <p className="text-sm text-slate-400">
            Structured symbol-first authoring with live Pint dimensional verification and SymPy simplification.
          </p>
        </div>

        {/* Live LaTeX & Numerical Computation Preview Badge */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-white/[0.08] bg-slate-900/90 px-4 py-2.5 shadow-tactile-card backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-medium text-slate-400">
              Formula:
            </span>
            <div className="text-sm font-bold text-slate-100 min-w-[70px]">
              {currentLatex ? (
                <KatexFormula math={currentLatex} />
              ) : (
                <span className="text-xs italic text-slate-500">Empty</span>
              )}
            </div>
          </div>

          {computedResult?.value !== null && computedResult?.value !== undefined && (
            <div className="flex items-center gap-1.5 pl-3 border-l border-white/10 text-xs font-mono text-cyan-300">
              <Calculator className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-slate-400">Preview:</span>
              <span className="font-bold text-white bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/40 shadow-inner">
                R ≈ {formatEvaluatedValue(computedResult.value)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Translation Error Alert */}
      {translationError && (
        <div className="rounded-xl border border-rose-800/80 bg-rose-950/60 p-4 text-xs text-rose-300 shadow-tactile-card flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold font-mono uppercase tracking-wider text-rose-400">Canvas Notice:</span>
            <span>{translationError}</span>
          </div>
        </div>
      )}

      {/* 1-Click Scientific Presets Bar */}
      <ScientificPresetsBar onSelectPreset={handleSelectPreset} />

      {/* Main Authoring Area */}
      <div className="grid grid-cols-1 gap-6">
        {/* Symbol-First Declaration Panel */}
        <VariableDeclarationPanel
          variables={variables}
          onVariablesChange={setVariables}
          usedSymbols={usedSymbols}
        />

        {/* Interactive Node Canvas */}
        <Card className="p-4 border-white/[0.08] bg-slate-900/80 backdrop-blur-xl shadow-tactile-card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              Symbolic Dataflow Canvas
            </h2>
            <span className="text-xs font-mono text-slate-400">
              Drag connections from output handles to operator inputs
            </span>
          </div>

          <SymbolicCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            declaredVariables={variables}
            onNodeDataChange={handleNodeDataChange}
            onAddNode={handleAddNode}
            onAutoLayout={handleAutoLayout}
            onClear={handleClear}
            onValidate={handleValidate}
            isValidating={isValidating}
          />
        </Card>

        {/* Validation Status Bar */}
        <ValidationStatusBar
          result={validationResult}
          isValidating={isValidating}
          onValidate={handleValidate}
        />

        {/* Canonical AST JSON Debug & Interactive Tree View */}
        {currentAst && (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Code2 className="h-4 w-4 text-cyan-400" />
                AST Tree Inspection &amp; Serialization
              </h3>
              <span className="text-xs font-mono text-cyan-400">
                Layer 1 Syntax Guard: PASS
              </span>
            </div>
            <AstVisualizer ast={currentAst} />
          </div>
        )}
      </div>
    </div>
  );
}
