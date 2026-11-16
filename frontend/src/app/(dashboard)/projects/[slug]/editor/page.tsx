"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  VariableSpec,
  ExprNode,
  ResearchProjectModel,
  EquationModel,
  VariableModel,
} from "@/types/contracts";
import { assertCanonicalAst } from "@/lib/ast_graph_converter";
import { fetchProjectBySlug, fetchVersionEquations, fetchVersionVariables } from "@/lib/api";
import { formatEvaluatedValue } from "@/lib/formula_evaluator";
import { useEquationCanvas } from "@/hooks/useEquationCanvas";

import { SymbolicCanvas } from "@/components/equations/canvas/SymbolicCanvas";
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
import { Code2, Sparkles, Layers, Calculator } from "lucide-react";

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
  const slug = (params?.slug as string) || "";

  const {
    nodes, edges, variables, currentAst, currentLatex, computedResult,
    validationResult, isValidating, translationError, replaceCanvas, cancelPendingValidation,
    handleVariablesChange, handleNodeDataChange, onNodesChange, onEdgesChange, onConnect,
    handleAddNode, handleAutoLayout, handleClear, handleValidate,
  } = useEquationCanvas();
  const [project, setProject] = useState<ResearchProjectModel | null>(null);
  const [projectLoading, setProjectLoading] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);
  const activeVersion = project?.versions?.[0] ?? null;

  // Presets populate only the local canvas; validation remains an explicit action.
  const handleSelectPreset = useCallback((preset: ScientificPreset) => {
    replaceCanvas(preset.ast, preset.variables);
  }, [replaceCanvas]);

  // Load the actual project/version records before describing the canvas context.
  useEffect(() => {
    let active = true;

    async function loadEditorContext() {
      let loadedProject: ResearchProjectModel | null = null;
      replaceCanvas(null, []);
      setProjectLoading(true);
      setProjectError(null);
      setProject(null);
      try {
        loadedProject = slug ? await fetchProjectBySlug(slug) : null;
        if (!active) return;
        setProject(loadedProject);

        const version = loadedProject?.versions?.[0];
        if (version) {
          let equations: EquationModel[];
          let apiVariables: VariableModel[];
          try {
            [equations, apiVariables] = await Promise.all([
              fetchVersionEquations(version.id),
              fetchVersionVariables(version.id),
            ]);
          } catch (cause) {
            if (!active) return;
            setProjectError(cause instanceof Error ? cause.message : "Version records could not be loaded.");
            replaceCanvas(null, []);
            return;
          }
          if (!active) return;

          const declaredVariables: VariableSpec[] = apiVariables.map((variable) => ({
            symbol: variable.symbol,
            name: variable.name,
            unit: variable.unit,
            domain: variable.domain as VariableSpec["domain"],
            latex_presentation: variable.latex_presentation,
          }));
          const equation = equations[0];
          if (equation?.canonical_ast_json) {
            assertCanonicalAst(equation.canonical_ast_json);
            const ast = equation.canonical_ast_json;
            replaceCanvas(ast, declaredVariables);
            return;
          }

          replaceCanvas(null, declaredVariables);
          return;
        }

        if (loadedProject) {
          replaceCanvas(null, []);
          return;
        }

        const urlParams = new URLSearchParams(window.location.search);
        const presetParam = urlParams.get("preset");
        const preset = presetParam
          ? CANONICAL_PRESETS.find((item) => item.id === presetParam || item.id.toLowerCase().includes(presetParam.toLowerCase()))
          : null;
        const initialAst = preset?.ast ?? INITIAL_AST;
        const initialVariables = preset?.variables ?? INITIAL_VARIABLES;
        replaceCanvas(initialAst, initialVariables);
      } catch (cause) {
        if (!active) return;
        if (loadedProject) {
          setProject(loadedProject);
          setProjectError(cause instanceof Error ? cause.message : "Project records could not be loaded.");
          replaceCanvas(null, []);
          return;
        }

        setProject(null);
        setProjectError(cause instanceof Error ? cause.message : "Project context could not be loaded.");
        replaceCanvas(INITIAL_AST, INITIAL_VARIABLES);
      } finally {
        if (active) setProjectLoading(false);
      }
    }

    loadEditorContext();
    return () => {
      active = false;
      cancelPendingValidation();
    };
  }, [slug, replaceCanvas, cancelPendingValidation]);

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

  if (projectLoading) {
    return (
      <div role="status" className="container mx-auto max-w-7xl p-6 text-sm text-slate-300">
        Loading project records…
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">
            <Layers className="h-4 w-4" />
            <span>Research equation workspace</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold text-slate-100 sm:text-3xl">
            {project?.title || "Local equation draft"}
          </h1>
          <p className="text-sm text-slate-400" aria-live="polite">
            {projectLoading
              ? "Loading project records…"
              : activeVersion
              ? `Project ${project?.slug} · Version ${activeVersion.version_number}: ${activeVersion.title}. Canvas edits are not saved automatically.`
              : project
              ? "No version is recorded for this project. Canvas edits remain local and are not persisted."
              : "Illustrative local draft. Canvas edits are not persisted to a project."}
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
              <span className="text-slate-400">Local calculation:</span>
              <span className="font-bold text-white bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/40 shadow-inner">
                R ≈ {formatEvaluatedValue(computedResult.value)}
              </span>
            </div>
          )}
        </div>
      </div>

      {projectError && (
        <div role="alert" className="border border-amber-700/70 bg-amber-950/30 p-3 text-sm text-amber-100">
          {project
            ? `Stored project records could not be loaded: ${projectError}. The canvas was cleared and no example data was substituted.`
            : `Project lookup failed: ${projectError}. This illustrative local draft is not associated with the requested project.`}
        </div>
      )}

      <p role="status" className="border border-slate-700 bg-slate-900/70 p-3 text-xs text-slate-300">
        Interactive checks are ad hoc API responses; they do not create persisted validation history. Recorded versions can be validated from their project page.
      </p>

      {/* Translation Error Alert */}
      {translationError && (
        <div role="alert" className="rounded-xl border border-rose-800/80 bg-rose-950/60 p-4 text-xs text-rose-300 shadow-tactile-card flex items-center justify-between">
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
          onVariablesChange={handleVariablesChange}
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
              <span className="text-xs font-mono text-slate-400">
                AST preview · not a validation result
              </span>
            </div>
            <AstVisualizer ast={currentAst} />
          </div>
        )}
      </div>
    </div>
  );
}
