"use client";

import React from "react";
import { FindingResult, FindingState } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Loader2,
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
    badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800",
    description: "Model passes dimensional homogeneity and symbolic equivalence checks.",
  },
  FAIL: {
    label: "FAIL",
    icon: XCircle,
    badgeClass: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/80 dark:text-rose-300 dark:border-rose-800",
    description: "Verification failed. Dimensional mismatch or mathematical contradiction detected.",
  },
  WARNING: {
    label: "WARNING",
    icon: AlertTriangle,
    badgeClass: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800",
    description: "Mathematical warning: potential singularity, boundary asymptote, or domain restriction.",
  },
  NOT_APPLICABLE: {
    label: "NOT APPLICABLE",
    icon: HelpCircle,
    badgeClass: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
    description: "Selected test layers are not applicable to this mathematical structure.",
  },
  INSUFFICIENT_DATA: {
    label: "INSUFFICIENT DATA",
    icon: HelpCircle,
    badgeClass: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/80 dark:text-orange-300 dark:border-orange-800",
    description: "Incomplete variable specifications or missing physical boundary constants.",
  },
  NEEDS_EXPERT_REVIEW: {
    label: "NEEDS EXPERT REVIEW",
    icon: AlertTriangle,
    badgeClass: "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-950/80 dark:text-purple-300 dark:border-purple-800",
    description: "Complex non-linear formulation requires peer-review academic oversight.",
  },
  NOT_YET_TESTED: {
    label: "NOT YET TESTED",
    icon: Clock,
    badgeClass: "bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-900 dark:text-slate-400 dark:border-slate-800",
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
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-3">
          {/* Status Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold tracking-wide uppercase ${config.badgeClass}`}
            data-testid="finding-state-badge"
          >
            {isValidating ? (
              <Loader2 className="h-4 w-4 animate-spin text-sky-600" />
            ) : (
              <StateIcon className="h-4 w-4 shrink-0" />
            )}
            <span>{isValidating ? "COMPUTING..." : config.label}</span>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              RCE Compute Sandbox Status
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {config.description}
            </p>
          </div>
        </div>

        {onValidate && (
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-50"
          >
            {isValidating && <Loader2 className="h-4 w-4 animate-spin" />}
            {isValidating ? "Verifying AST..." : "Run Compute Verification"}
          </button>
        )}
      </div>

      {/* Verification Diagnostics and Simplification */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dimensional Verification Card */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              {result?.dimensions_verified ? (
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-slate-400" />
              )}
              Dimensional Homogeneity (Pint)
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                result?.dimensions_verified
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
              }`}
            >
              {result?.dimensions_verified ? "VERIFIED" : "UNVERIFIED"}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {result?.message || "Submit formula to verify physical unit consistency."}
          </p>
          {result?.diagnostic_code && (
            <div className="mt-2 text-[11px] font-mono text-slate-600 dark:text-slate-400">
              Code: <span className="font-semibold">{result.diagnostic_code}</span>
            </div>
          )}
        </div>

        {/* SymPy Symbolic Simplification Card */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              SymPy Symbolic Simplification
            </span>
            {result?.job_id && (
              <span className="text-[10px] font-mono text-slate-400">
                Job: {result.job_id.slice(0, 8)}
              </span>
            )}
          </div>
          <div className="min-h-[36px] flex items-center">
            {result?.symbolic_simplification ? (
              <div className="font-mono text-xs bg-white dark:bg-slate-900 px-3 py-1.5 rounded border border-slate-200 dark:border-slate-700">
                <KatexFormula math={result.symbolic_simplification} />
              </div>
            ) : (
              <span className="text-xs italic text-slate-400">
                Awaiting symbolic evaluation...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Diagnostics List (if any) */}
      {result?.diagnostics && result.diagnostics.length > 0 && (
        <div className="mt-3 rounded-lg bg-slate-100/70 p-3 text-xs dark:bg-slate-800/60">
          <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
            Sandbox Diagnostics:
          </span>
          <ul className="list-disc list-inside space-y-0.5 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
            {result.diagnostics.map((diag, idx) => (
              <li key={idx}>{diag}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
