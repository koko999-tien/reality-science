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

import { SymbolicCanvas } from "@/components/equations/canvas/SymbolicCanvas";
import { NodeTypeToAdd } from "@/components/equations/canvas/CanvasToolbar";
import { VariableDeclarationPanel } from "@/components/equations/VariableDeclarationPanel";
import { ValidationStatusBar } from "@/components/equations/ValidationStatusBar";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { Card } from "@/components/ui/Card";
import { Code2, Sparkles, BookOpen, Layers } from "lucide-react";

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
  const [validationResult, setValidationResult] = useState<FindingResult | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [nodeIdCounter, setNodeIdCounter] = useState<number>(100);

  // Initialize canvas with initial AST layout
  useEffect(() => {
    const { nodes: initialNodes, edges: initialEdges } = astToGraph(INITIAL_AST, INITIAL_VARIABLES);
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, []);

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

  // Synchronize AST and live LaTeX when nodes or edges change
  const syncAst = useCallback(
    (currentNodes: MathCanvasNode[], currentEdges: MathCanvasEdge[]) => {
      try {
        const ast = graphToAst(currentNodes, currentEdges, variables);
        const latex = exprNodeToLatex(ast);
        setCurrentAst(ast);
        setCurrentLatex(latex);
        setTranslationError(null);

        // Update EquationRootNode with live LaTeX if present
        setNodes((prevNodes) =>
          prevNodes.map((n) =>
            n.type === "equationRootNode"
              ? { ...n, data: { ...n.data, latex } }
              : n
          )
        );
      } catch (err) {
        if (err instanceof TranslationError) {
          setTranslationError(err.message);
        }
      }
    },
    [variables]
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
            animated: true,
            style: { stroke: "#0284c7", strokeWidth: 2 },
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
            data: { name: "R", latex: currentLatex },
          };
          break;
      }

      setNodes((nds) => [...nds, newNode]);
    },
    [nodeIdCounter, nodes.length, variables, currentLatex]
  );

  const handleAutoLayout = useCallback(() => {
    try {
      const ast = graphToAst(nodes, edges, variables);
      const { nodes: layoutNodes, edges: layoutEdges } = astToGraph(ast, variables);
      setNodes(layoutNodes);
      setEdges(layoutEdges);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-600 dark:text-sky-400">
            <Layers className="h-4 w-4" />
            <span>Interactive Symbolic Canvas</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            Mathematical Model Editor — {slug}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Structured symbol-first authoring with live Pint dimensional verification and SymPy simplification.
          </p>
        </div>

        {/* Live LaTeX preview badge */}
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Formula:
          </span>
          <div className="text-sm font-bold text-slate-900 dark:text-slate-100 min-w-[80px]">
            {currentLatex ? (
              <KatexFormula math={currentLatex} />
            ) : (
              <span className="text-xs italic text-slate-400">Empty</span>
            )}
          </div>
        </div>
      </div>

      {/* Translation Error Alert */}
      {translationError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider">Canvas Notice:</span>
            <span>{translationError}</span>
          </div>
        </div>
      )}

      {/* Main Authoring Area */}
      <div className="grid grid-cols-1 gap-6">
        {/* Symbol-First Declaration Panel */}
        <VariableDeclarationPanel
          variables={variables}
          onVariablesChange={setVariables}
          usedSymbols={usedSymbols}
        />

        {/* Interactive Node Canvas */}
        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-sky-500" />
              Symbolic Dataflow Canvas
            </h2>
            <span className="text-xs text-slate-500">
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

        {/* Canonical AST JSON Debug / Export View */}
        {currentAst && (
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Code2 className="h-4 w-4 text-slate-500" />
                Canonical ExprNode JSON Representation
              </h3>
              <span className="text-xs font-mono text-slate-400">
                Layer 1 Syntax Guard: PASS
              </span>
            </div>
            <pre className="max-h-60 overflow-y-auto rounded-lg bg-slate-950 p-4 font-mono text-xs text-emerald-400">
              {JSON.stringify(currentAst, null, 2)}
            </pre>
          </Card>
        )}
      </div>
    </div>
  );
}
