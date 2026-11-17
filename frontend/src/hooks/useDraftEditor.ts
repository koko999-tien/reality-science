"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { createVersion, fetchProjectBySlug, fetchVersionDraft, saveVersionDraft } from "@/lib/api";
import { assertCanonicalAst } from "@/lib/ast_graph_converter";
import type { DraftContent, DraftSnapshot, ExprNode, ResearchProjectModel, UnitSpec, VariableSpec } from "@/types/contracts";

type CanvasSnapshot = { ast: ExprNode | null; latex: string; variables: VariableSpec[]; units: UnitSpec[] };
function declarations(snapshot: DraftSnapshot): VariableSpec[] {
  return snapshot.variables.map((v) => ({ symbol: v.symbol, name: v.name, unit: v.unit,
    domain: v.domain as VariableSpec["domain"], latex_presentation: v.latex_presentation ?? undefined }));
}
// Ignore server IDs/default nulls and key ordering when comparing saved content.
export function draftContentKey(content: unknown): string {
  return JSON.stringify(content, (key, value) => {
    if (key === "id" || value === null) return undefined;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)));
    }
    return value;
  });
}
export function canvasDraft(snapshot: DraftSnapshot | null, canvas: CanvasSnapshot,
  primaryEquationId: string | null | undefined = snapshot?.equations[0]?.id): DraftContent {
  const first = snapshot?.equations.find((equation) => equation.id === primaryEquationId);
  const firstAst = first?.canonical_ast_json;
  if (firstAst) assertCanonicalAst(firstAst);
  const unchanged = first && firstAst && draftContentKey(firstAst) === draftContentKey(canvas.ast);
  return {
    equations: [
      ...(canvas.ast ? [{ ...(first ? { id: first.id } : {}), label: first?.label ?? "Primary equation",
        latex_raw: unchanged ? first.latex_raw : canvas.latex,
        canonical_ast_json: unchanged ? firstAst : canvas.ast }] : []),
      ...(snapshot?.equations.filter((e) => e.id !== primaryEquationId).map((e) => {
        assertCanonicalAst(e.canonical_ast_json);
        return { id: e.id, label: e.label, latex_raw: e.latex_raw, canonical_ast_json: e.canonical_ast_json };
      }) ?? []),
    ], variables: canvas.variables, units: canvas.units,
  };
}

export function useDraftEditor(slug: string, replaceCanvas: (ast: ExprNode | null, variables: VariableSpec[], units?: UnitSpec[]) => void,
  getSaveSnapshot: () => CanvasSnapshot, cancelPendingValidation: () => void) {
  const [project, setProject] = useState<ResearchProjectModel | null>(null);
  const [snapshot, setSnapshot] = useState<DraftSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState("");
  const [primaryEquationId, setPrimaryEquationId] = useState<string | null>(null);
  const generation = useRef(0);
  const busy = useRef(false);
  const mutation = useRef(0);

  const load = useCallback(async (versionId?: string) => {
    const request = ++generation.current;
    setLoading(true); setError(null); setSaveError(null); setSaveMessage("");
    setSnapshot(null); setPrimaryEquationId(null); setSavedKey(null); replaceCanvas(null, []);
    try {
      const project = await fetchProjectBySlug(slug);
      if (request !== generation.current) return;
      setProject(project);
      const id = versionId || new URLSearchParams(window.location.search).get("version") || project.versions?.[0]?.id;
      if (!id) return;
      if (!project.versions?.some((v) => v.id === id)) throw new Error("The selected version is not available in this project.");
      const loaded = await fetchVersionDraft(id);
      if (request !== generation.current) return;
      const ast = loaded.equations[0]?.canonical_ast_json ?? null;
      if (ast) assertCanonicalAst(ast);
      replaceCanvas(ast, declarations(loaded), loaded.units);
      setSnapshot(loaded);
      setPrimaryEquationId(loaded.equations[0]?.id ?? null);
      setSavedKey(draftContentKey(canvasDraft(loaded, getSaveSnapshot())));
      const url = new URL(window.location.href); url.searchParams.set("version", id);
      window.history.replaceState(null, "", url);
    } catch (cause) {
      if (request === generation.current) setError(cause instanceof Error ? cause.message : "Draft could not be loaded.");
    } finally { if (request === generation.current) setLoading(false); }
  }, [slug, replaceCanvas, getSaveSnapshot]);

  useEffect(() => {
    const lifecycle = generation;
    setProject(null); mutation.current++; busy.current = false; setSaving(false); setCreating(false);
    void load();
    return () => { lifecycle.current++; cancelPendingValidation(); };
  }, [load, cancelPendingValidation]);

  const create = async (title: string) => {
    if (busy.current) return;
    busy.current = true; setSaving(true); setCreating(true); setSaveError(null);
    const operation = ++mutation.current;
    const request = generation.current;
    try {
      const version = await createVersion(slug, title);
      if (request === generation.current) await load(version.id);
    } catch (cause) {
      if (request === generation.current) setSaveError(cause instanceof Error ? cause.message : "Version could not be created.");
    } finally { if (operation === mutation.current) { busy.current = false; setSaving(false); setCreating(false); } }
  };

  const save = async () => {
    if (!snapshot || busy.current) return;
    busy.current = true; setSaving(true); setSaveError(null); setSaveMessage("");
    const operation = ++mutation.current;
    const request = generation.current;
    try {
      const canvas = getSaveSnapshot();
      const content = canvasDraft(snapshot, canvas, primaryEquationId);
      const key = draftContentKey(content);
      const saved = await saveVersionDraft(snapshot.version.id, snapshot.version.revision!, content);
      if (request !== generation.current) return;
      setSnapshot(saved); setSavedKey(key);
      const existingIds = new Set(content.equations.flatMap((equation) => equation.id ? [equation.id] : []));
      setPrimaryEquationId(canvas.ast
        ? primaryEquationId ?? saved.equations.find((equation) => !existingIds.has(equation.id))?.id ?? null
        : null);
      setSaveMessage(`Saved revision ${saved.version.revision}.`);
      // Never hydrate the canvas from a save response: edits may have continued.
    } catch (cause) {
      if (request === generation.current) setSaveError(cause instanceof Error ? cause.message : "Draft was not saved.");
    } finally {
      if (operation === mutation.current) { busy.current = false; setSaving(false); }
    }
  };
  const restore = (saved: DraftSnapshot, key: string, primary: string | null) => {
    setSnapshot(saved); setSavedKey(key); setPrimaryEquationId(primary);
    setSaveMessage(""); setSaveError(null);
  };
  return { project, snapshot, primaryEquationId, loading, error, saveError, saving, creating, savedKey, saveMessage, load, create, save, restore };
}
