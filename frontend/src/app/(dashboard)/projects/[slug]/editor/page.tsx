"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { formatEvaluatedValue } from "@/lib/formula_evaluator";
import { useEquationCanvas } from "@/hooks/useEquationCanvas";
import { canvasDraft, draftContentKey, useDraftEditor } from "@/hooks/useDraftEditor";
import { UnitDefinitionsPanel } from "@/components/equations/UnitDefinitionsPanel";
import { useDraftRecovery } from "@/hooks/useDraftRecovery";

import { SymbolicCanvas } from "@/components/equations/canvas/SymbolicCanvas";
import {
  ScientificPresetsBar,
  type ScientificPreset,
} from "@/components/equations/canvas/ScientificPresetsBar";
import { VariableDeclarationPanel } from "@/components/equations/VariableDeclarationPanel";
import { ValidationStatusBar } from "@/components/equations/ValidationStatusBar";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { AstVisualizer } from "@/components/equations/AstVisualizer";
import { Card } from "@/components/ui/Card";
import { Code2, Sparkles, Layers, Calculator } from "lucide-react";

export default function EquationEditorPage({
  params: _params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const params = useParams();
  const slug = (params?.slug as string) || "";

  const {
    nodes, edges, variables, units, currentAst, currentLatex, computedResult,
    validationResult, isValidating, translationError, replaceCanvas, restoreCanvas, getCanvasSnapshot, cancelPendingValidation,
    handleVariablesChange, handleNodeDataChange, onNodesChange, onEdgesChange, onConnect,
    handleAddNode, handleAutoLayout, handleClear, handleValidate, handleUnitsChange, getSaveSnapshot,
  } = useEquationCanvas();
  const draft = useDraftEditor(slug, replaceCanvas, getSaveSnapshot, cancelPendingValidation);
  const { project, loading: projectLoading, error: projectError } = draft;
  const activeVersion = draft.snapshot?.version ?? null;
  const [versionTitle, setVersionTitle] = useState("");
  const editable = !draft.creating && !!project?.can_edit && !!activeVersion && !activeVersion.is_frozen &&
    !project.is_frozen && activeVersion.publication_status === "draft" && !activeVersion.content_hash;
  const currentKey = useMemo(() => {
    try { return draftContentKey(canvasDraft(draft.snapshot, { ast: currentAst, latex: currentLatex, variables, units }, draft.primaryEquationId)); }
    catch { return null; }
  }, [draft.snapshot, draft.primaryEquationId, currentAst, currentLatex, variables, units]);
  const dirty = !!draft.snapshot && (currentKey !== draft.savedKey || (nodes.length > 0 && currentAst === null));
  const recoveryMessage = useDraftRecovery(slug, draft, dirty, editable, getCanvasSnapshot, restoreCanvas);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const switchVersion = (id: string) => {
    if (!dirty || window.confirm("Discard unsaved edits and load the saved version?")) void draft.load(id);
  };

  // Presets populate only the local canvas; validation remains an explicit action.
  const handleSelectPreset = useCallback((preset: ScientificPreset) => {
    replaceCanvas(preset.ast, preset.variables, units);
  }, [replaceCanvas, units]);

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
            {project?.title || "Equation workspace"}
          </h1>
          <p className="text-sm text-slate-400" aria-live="polite">
            {projectLoading
              ? "Loading project records…"
              : activeVersion
               ? `Project ${project?.slug} · Version ${activeVersion.version_number}: ${activeVersion.title}. Revision ${activeVersion.revision}.`
              : project
               ? "No version is recorded for this project. Create a draft to begin."
               : "Project records are unavailable."}
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
          {`Stored project records could not be loaded: ${projectError}.`}
          <button type="button" className="ml-3 underline" onClick={() => void draft.load()}>Retry</button>
        </div>
      )}

      {project && <section aria-label="Draft persistence" className="space-y-3 border border-slate-700 p-4">
        <div className="flex flex-wrap items-end gap-3">
          {!!project.versions?.length && <label className="text-sm">Version
            <select aria-label="Version" value={activeVersion?.id ?? ""} disabled={draft.saving}
              onChange={(event) => switchVersion(event.target.value)} className="ml-2 min-h-11 border border-slate-600 bg-slate-950 px-3">
              {!activeVersion && <option value="">Choose version</option>}
              {project.versions.map((v) => <option key={v.id} value={v.id}>{`v${v.version_number} · ${v.title}`}</option>)}
            </select>
          </label>}
          {project.can_edit && project.visibility === "private_draft" && !project.is_frozen && <>
            <label className="text-sm">New draft title<input aria-label="New draft title" value={versionTitle} maxLength={255}
              onChange={(e) => setVersionTitle(e.target.value)} className="ml-2 min-h-11 border border-slate-600 bg-slate-950 px-3" /></label>
            <button type="button" disabled={draft.saving || !versionTitle.trim()} className="min-h-11 border border-slate-600 px-4 disabled:opacity-50"
              onClick={() => { if (!dirty || window.confirm("Discard unsaved edits and create an empty draft?")) void draft.create(versionTitle.trim()); }}>Create draft</button>
          </>}
          {editable && <button type="button" disabled={draft.saving || !dirty || (nodes.length > 0 && !currentAst)}
            onClick={() => void draft.save()} className="min-h-11 bg-cyan-600 px-4 font-semibold text-white disabled:opacity-50">{draft.saving ? "Saving…" : "Save draft"}</button>}
          {activeVersion && <button type="button" disabled={draft.saving} onClick={() => switchVersion(activeVersion.id)} className="min-h-11 border border-slate-600 px-4">Reload saved draft</button>}
        </div>
        <p role="status" aria-live="polite" className="text-sm text-slate-300">{draft.saving ? "Saving to the research API…" : dirty ? "Unsaved changes" : draft.saveMessage || (activeVersion ? "Saved draft loaded." : "")}</p>
        {activeVersion && !editable && !draft.creating && <p className="text-sm text-amber-200">This version is read-only.</p>}
        {(draft.snapshot?.equations.length ?? 0) > 1 && <p className="text-xs text-slate-400">The canvas edits the primary equation. Other equations are retained when saving.</p>}
        {draft.saveError && <p role="alert" className="text-sm text-rose-300">{draft.saveError}</p>}
        {recoveryMessage && <p role="status" className="text-sm text-amber-200">{recoveryMessage}</p>}
      </section>}

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
      <fieldset disabled={!editable} inert={!editable} className="min-w-0 space-y-6">
      <ScientificPresetsBar onSelectPreset={handleSelectPreset} />

      {/* Main Authoring Area */}
      <div className="grid grid-cols-1 gap-6">
        {/* Symbol-First Declaration Panel */}
        <VariableDeclarationPanel
          variables={variables}
          onVariablesChange={handleVariablesChange}
          usedSymbols={usedSymbols}
        />
        <UnitDefinitionsPanel units={units} onChange={handleUnitsChange} />

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
            onNodesChange={editable ? onNodesChange : () => {}}
            onEdgesChange={editable ? onEdgesChange : () => {}}
            onConnect={editable ? onConnect : () => {}}
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
      </fieldset>
    </div>
  );
}
