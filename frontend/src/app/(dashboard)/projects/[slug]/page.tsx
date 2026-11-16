"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import {
  fetchProjectBySlug,
  fetchVersionEquations,
  fetchVersionVariables,
  fetchVersionClaims,
  fetchVersionRuns,
  validateVersion,
  exportVersionZip,
} from "@/lib/api";
import {
  ResearchProjectModel,
  EquationModel,
  VariableModel,
  ClaimModel,
  ValidationRunModel,
  LayerFinding,
} from "@/types/contracts";
import { LayerPipelineMatrix } from "@/components/equations/LayerPipelineMatrix";
import {
  Download,
  FileCheck2,
  Play,
  Layers,
  Variable as VariableIcon,
  GitBranch,
  Lock,
  Globe,
  Loader2,
  RefreshCw,
  ArrowLeft,
  Sparkles,
} from "lucide-react";

export default function ProjectDetailsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);

  const [project, setProject] = useState<ResearchProjectModel | null>(null);
  const [equations, setEquations] = useState<EquationModel[]>([]);
  const [variables, setVariables] = useState<VariableModel[]>([]);
  const [claims, setClaims] = useState<ClaimModel[]>([]);
  const [runs, setRuns] = useState<ValidationRunModel[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [dataErrors, setDataErrors] = useState<string[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "equations" | "variables" | "claims" | "history">("overview");

  const activeVersion = project?.versions && project.versions.length > 0 ? project.versions[0] : null;
  const versionId = activeVersion?.id;

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setDataErrors([]);
    setProject(null);
    setEquations([]);
    setVariables([]);
    setClaims([]);
    setRuns([]);
    try {
      const proj = await fetchProjectBySlug(slug);
      setProject(proj);

      const vId = proj.versions && proj.versions.length > 0 ? proj.versions[0].id : null;
      if (vId) {
        const results = await Promise.allSettled([
          fetchVersionEquations(vId),
          fetchVersionVariables(vId),
          fetchVersionClaims(vId),
          fetchVersionRuns(vId),
        ]);
        const [eqs, vars, clms, valRuns] = results;
        if (eqs.status === "fulfilled") setEquations(eqs.value);
        if (vars.status === "fulfilled") setVariables(vars.value);
        if (clms.status === "fulfilled") setClaims(clms.value);
        if (valRuns.status === "fulfilled") setRuns(valRuns.value);
        setDataErrors(results.flatMap((result, index) => result.status === "rejected"
          ? [`${["Equations", "Variables", "Claims", "Validation history"][index]} could not be loaded.`]
          : []));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load project details.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunValidation = async () => {
    if (!versionId) return;
    setIsValidating(true);
    setActionError(null);
    try {
      const newRun = await validateVersion(versionId);
      setRuns((prev) => [newRun, ...prev]);
    } catch (err: any) {
      setActionError(`Validation was not completed: ${err.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  const latestRun = runs.length > 0 ? runs[0] : null;

  // Convert latest run findings to LayerFinding map for LayerPipelineMatrix
  const latestLayers: Record<number, LayerFinding> = {};
  if (latestRun && latestRun.findings) {
    for (const f of latestRun.findings) {
      latestLayers[f.layer] = {
        layer: f.layer,
        name: f.message.split(":")[0] || `Layer ${f.layer}`,
        state: f.state,
        diagnostic_code: f.diagnostic_code,
        message: f.message,
        diagnostics:
          Array.isArray(f.diagnostics)
            ? f.diagnostics
            : f.diagnostics?.diagnostics || [],
        details: f.diagnostics?.details || undefined,
      };
    }
  }

  if (isLoading && !project) {
    return <div role="status" className="container mx-auto max-w-7xl p-6 text-sm text-slate-600 dark:text-slate-300">Loading project records…</div>;
  }

  if (error && !project) {
    return (
      <div className="container mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-2xl font-semibold">Project data unavailable</h1>
        <p role="alert" className="border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">{error}</p>
        <button type="button" onClick={loadData} disabled={isLoading} className="min-h-11 border border-slate-400 px-4 font-semibold disabled:opacity-50">Retry</button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {project?.title || (isLoading ? "Loading project" : "Project unavailable")}
            </h1>
            {project?.visibility && (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <Globe className="w-3 h-3" />
                {project.visibility}
              </span>
            )}
            {project?.is_frozen && (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                <Lock className="w-3 h-3" /> Frozen Immutable
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {project?.description || "No project description provided."}
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href={`/projects/${slug}/editor`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20 hover:from-sky-400 hover:to-indigo-500 transition-all focus:outline-none focus:ring-2 focus:ring-sky-400"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-200" />
            Open equation editor &rarr;
          </Link>

          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-slate-200 bg-white text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>

          {versionId && (
            <button
              type="button"
              onClick={async () => {
                setActionError(null);
                try {
                  const blob = await exportVersionZip(versionId);
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = `research_bundle_${versionId}.zip`;
                  link.click();
                  URL.revokeObjectURL(url);
                } catch (err) {
                  setActionError(err instanceof Error ? err.message : "Export failed.");
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-slate-200 bg-white text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 transition"
            >
              <Download className="w-3.5 h-3.5" />
              Export Bundle (.ZIP)
            </button>
          )}

          <button
            onClick={handleRunValidation}
            disabled={isValidating || !versionId}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white shadow-sm hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition"
          >
            {isValidating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            {isValidating ? "Validating version..." : "Run version validation"}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          <div><strong>Project data unavailable.</strong> {error}</div>
          <button type="button" onClick={loadData} disabled={isLoading} className="min-h-10 border border-current px-3 font-semibold disabled:opacity-50">
            {isLoading ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}
      {dataErrors.length > 0 && (
        <div role="status" className="border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          Some project records are unavailable: {dataErrors.join(" ")}
        </div>
      )}
      {actionError && <p role="alert" className="border border-rose-300 bg-rose-50 p-3 text-sm text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">{actionError}</p>}

      {/* Status axes remain independent; unprovided fields are shown as unrecorded. */}
      <section aria-label="Research status" className="grid gap-3 border-y border-slate-200 py-4 dark:border-slate-800 sm:grid-cols-3">
        <div><div className="text-xs text-slate-500">Publication</div><strong className="text-sm">{activeVersion?.publication_status || "Not recorded"}</strong></div>
        <div><div className="text-xs text-slate-500">Validation</div><strong className="text-sm">{latestRun?.overall_state || "Not tested"}</strong></div>
        <div><div className="text-xs text-slate-500">Evidence maturity</div><strong className="text-sm">Not recorded by API</strong></div>
      </section>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">Equations</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{equations.length}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">Variables</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{variables.length}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
            <VariableIcon className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">Epistemic Claims</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{claims.length}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-purple-50 text-purple-600 dark:bg-purple-950 dark:text-purple-400">
            <GitBranch className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">Latest validation state</div>
            <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {latestRun ? latestRun.overall_state : "NOT TESTED"}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
            <FileCheck2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-3 text-sm font-medium transition ${
              activeTab === "overview"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Validation findings by layer
          </button>
          <button
            onClick={() => setActiveTab("equations")}
            className={`pb-3 text-sm font-medium transition ${
              activeTab === "equations"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Equations ({equations.length})
          </button>
          <button
            onClick={() => setActiveTab("variables")}
            className={`pb-3 text-sm font-medium transition ${
              activeTab === "variables"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Variables ({variables.length})
          </button>
          <button
            onClick={() => setActiveTab("claims")}
            className={`pb-3 text-sm font-medium transition ${
              activeTab === "claims"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Epistemic Claims ({claims.length})
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`pb-3 text-sm font-medium transition ${
              activeTab === "history"
                ? "border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Validation Runs ({runs.length})
          </button>
        </nav>
      </div>

      {/* Tab Panels */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <LayerPipelineMatrix layers={latestLayers} />
        </div>
      )}

      {activeTab === "equations" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 overflow-hidden divide-y divide-slate-200 dark:divide-slate-800">
          {equations.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400 flex flex-col items-center justify-center gap-3">
              <p>No equations are recorded for this version. The editor opens a local draft; its changes are not saved to project records.</p>
              <Link
                href={`/projects/${slug}/editor`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-sky-500 to-indigo-600 text-white shadow-md shadow-sky-500/20 hover:from-sky-400 hover:to-indigo-500 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5 text-sky-200" />
                Open local equation editor &rarr;
              </Link>
            </div>
          ) : (
            equations.map((eq) => (
              <div key={eq.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">{eq.label}</span>
                  <span className="text-xs font-mono text-slate-400">{eq.id.slice(0, 8)}</span>
                </div>
                <div className="p-2 rounded bg-slate-50 dark:bg-slate-900 font-mono text-xs text-slate-700 dark:text-slate-300">
                  {eq.latex_raw}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "variables" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 overflow-hidden">
          {variables.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
              No variables are recorded for this version. The editor can hold a local draft, but its changes are not saved to project records.
            </div>
          ) : (
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
              <thead className="bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">SI Unit</th>
                  <th className="p-3">Domain</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {variables.map((v) => (
                  <tr key={v.id}>
                    <td className="p-3 font-mono font-bold text-slate-900 dark:text-slate-100">{v.symbol}</td>
                    <td className="p-3">{v.name}</td>
                    <td className="p-3 font-mono">{v.unit}</td>
                    <td className="p-3 capitalize">{v.domain}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === "claims" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 overflow-hidden divide-y divide-slate-200 dark:divide-slate-800">
          {claims.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
              No epistemic claims defined.
            </div>
          ) : (
            claims.map((c) => (
              <div key={c.id} className="p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">{c.claim_code}</span>
                  <span className="text-xs px-2 py-0.5 rounded font-medium bg-slate-100 dark:bg-slate-800">
                    {c.epistemic_state}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300">{c.statement}</p>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "history" && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 overflow-hidden divide-y divide-slate-200 dark:divide-slate-800">
          {runs.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
              No validation runs recorded. Run validation on this version to create a persisted history entry.
            </div>
          ) : (
            runs.map((r) => (
              <div key={r.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs font-mono text-slate-800 dark:text-slate-200">
                      Run #{r.id.slice(0, 8)}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                        r.overall_state === "PASS"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : r.overall_state === "FAIL"
                          ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                          : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                      }`}
                    >
                      {r.overall_state}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {r.completed_at ? new Date(r.completed_at).toLocaleString() : "Running"}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  {r.findings ? `${r.findings.length} layer findings recorded` : "No findings detail"}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
