"use client";

import React from "react";
import { FindingResult, FindingState } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { LayerPipelineMatrix } from "@/components/equations/LayerPipelineMatrix";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  Cpu,
} from "lucide-react";

interface ValidationStatusBarProps {
  result: FindingResult | null;
  isValidating?: boolean;
  onValidate?: () => void;
  className?: string;
}

const STATE_CONFIG: Record<
  FindingState,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badgeClass: string;
    description: string;
  }
> = {
  PASS: {
    label: "PASS",
    icon: CheckCircle2,
    badgeClass: "bg-emerald-950/80 text-emerald-300 border-emerald-700/80 shadow-sm shadow-emerald-500/20",
    description: "Model passes dimensional homogeneity, boundary stability, and symbolic equivalence checks.",
  },
  FAIL: {
    label: "FAIL",
    icon: XCircle,
    badgeClass: "bg-rose-950/80 text-rose-300 border-rose-700/80 shadow-sm shadow-rose-500/20",
    description: "Verification failed. Dimensional mismatch or mathematical contradiction detected.",
  },
  WARNING: {
    label: "WARNING",
    icon: AlertTriangle,
    badgeClass: "bg-amber-950/80 text-amber-300 border-amber-700/80 shadow-sm shadow-amber-500/20",
    description: "Mathematical warning: potential singularity, boundary asymptote, or domain restriction.",
  },
  NOT_APPLICABLE: {
    label: "NOT APPLICABLE",
    icon: HelpCircle,
    badgeClass: "bg-slate-800 text-slate-300 border-slate-700",
    description: "Selected test layers are not applicable to this mathematical structure.",
  },
  INSUFFICIENT_DATA: {
    label: "INSUFFICIENT DATA",
    icon: HelpCircle,
    badgeClass: "bg-orange-950/80 text-orange-300 border-orange-700/80 shadow-sm shadow-orange-500/20",
    description: "Incomplete variable specifications or missing physical boundary constants.",
  },
  NEEDS_EXPERT_REVIEW: {
    label: "NEEDS EXPERT REVIEW",
    icon: AlertTriangle,
    badgeClass: "bg-purple-950/80 text-purple-300 border-purple-700/80 shadow-sm shadow-purple-500/20",
    description: "Complex non-linear formulation requires peer-review academic oversight.",
  },
  NOT_YET_TESTED: {
    label: "NOT YET TESTED",
    icon: Clock,
    badgeClass: "bg-slate-900 text-slate-400 border-slate-800",
    description: "Canvas expression has not yet been submitted to the compute verification sandbox.",
  },
};

export const ValidationStatusBar: React.FC<ValidationStatusBarProps> = ({
  result,
  isValidating = false,
  onValidate,
  className = "",
}) => {
  const currentState: FindingState = result ? result.state : "NOT_YET_TESTED";
  const config = STATE_CONFIG[currentState] || STATE_CONFIG.NOT_YET_TESTED;
  const StateIcon = config.icon;

  return (
    <div
      className={`rounded-2xl border border-slate-700/60 bg-slate-900/90 backdrop-blur-xl p-5 shadow-2xl ${className}`}
      data-testid="validation-status-bar"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          {/* Status Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold tracking-wide uppercase ${config.badgeClass}`}
            data-testid="finding-state-badge"
          >
            {isValidating ? (
              <Loader2 className="h-4 w-4 animate-spin text-sky-400" />
            ) : (
              <StateIcon className="h-4 w-4 shrink-0" />
            )}
            <span>{isValidating ? "COMPUTING..." : config.label}</span>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
              6-Layer Reality Constraint Pipeline Status
            </h3>
            <p className="text-xs text-slate-400">
              {config.description}
            </p>
          </div>
        </div>

        {onValidate && (
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-sky-500/20 transition-all hover:from-sky-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-sky-400 disabled:opacity-50 cursor-pointer"
          >
            {isValidating && <Loader2 className="h-4 w-4 animate-spin" />}
            {isValidating ? "Verifying AST..." : "Run Compute Verification"}
          </button>
        )}
      </div>

      {/* Verification Diagnostics and Simplification */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dimensional Verification Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 shadow-inner">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              {result?.dimensions_verified ? (
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-slate-500" />
              )}
              Dimensional Homogeneity (SI Standard)
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                result?.dimensions_verified
                  ? "bg-emerald-950/80 text-emerald-300 border-emerald-800/80"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {result?.dimensions_verified ? "VERIFIED" : "UNVERIFIED"}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            {result?.message || "Submit formula to verify physical unit consistency."}
          </p>
          {result?.diagnostic_code && (
            <div className="mt-2 text-[11px] font-mono text-slate-300">
              Code: <span className="font-semibold text-cyan-400">{result.diagnostic_code}</span>
            </div>
          )}
        </div>

        {/* SymPy Symbolic Simplification Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 shadow-inner">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-300">
              Symbolic Simplification (SymPy CAS)
            </span>
            {result?.job_id && (
              <span className="text-[10px] font-mono text-slate-500">
                Job: {result.job_id.slice(0, 8)}
              </span>
            )}
          </div>
          <div className="min-h-[36px] flex items-center">
            {result?.symbolic_simplification ? (
              <div className="font-mono text-xs bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-700/80 text-emerald-400">
                <KatexFormula math={result.symbolic_simplification} />
              </div>
            ) : (
              <span className="text-xs italic text-slate-500">
                Awaiting symbolic evaluation...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Diagnostics List (if any) */}
      {result?.diagnostics && result.diagnostics.length > 0 && (
        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/80 p-3.5 text-xs">
          <span className="font-semibold text-slate-300 block mb-1.5">
            Sandbox Diagnostics:
          </span>
          <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
            {result.diagnostics.map((diag, idx) => (
              <li key={idx}>{diag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 6-Layer Reality Constraint Pipeline Matrix */}
      {result?.layer_findings && (
        <div className="mt-4">
          <LayerPipelineMatrix layers={result.layer_findings} />
        </div>
      )}
    </div>
  );
};
