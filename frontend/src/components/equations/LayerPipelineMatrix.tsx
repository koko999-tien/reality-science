"use client";

import React, { useState } from "react";
import { FindingState, LayerFinding } from "@/types/contracts";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Binary,
  Layers,
  Ruler,
  Atom,
  LineChart,
  GitBranch,
} from "lucide-react";

interface LayerPipelineMatrixProps {
  layers?: Record<number, LayerFinding>;
  className?: string;
}

const LAYER_METADATA: Record<
  number,
  {
    title: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  1: {
    title: "Layer 1: Syntax & Semantics",
    description: "AST grammar validation, complexity bounds (depth <= 15, node <= 100), symbol resolution.",
    icon: Binary,
  },
  2: {
    title: "Layer 2: Boundary & Singularities",
    description: "Symbolic pole detection, division-by-zero checks, domain asymptotics, SymPy simplification.",
    icon: Layers,
  },
  3: {
    title: "Layer 3: Dimensional Analysis",
    description: "Dimensional findings for declared variables and units, when returned by the backend.",
    icon: Ruler,
  },
  4: {
    title: "Layer 4: Physical Laws & Invariants",
    description: "Relativistic speed of light invariant (v <= c), energy & momentum conservation.",
    icon: Atom,
  },
  5: {
    title: "Layer 5: Empirical Correlation",
    description: "Statistical observation dataset fitting, chi-square, reduced chi-square, pull analysis.",
    icon: LineChart,
  },
  6: {
    title: "Layer 6: Definition Pending",
    description: "The project documentation has conflicting definitions for this layer.",
    icon: Layers,
  },
};

const STATE_STYLES: Record<
  FindingState,
  {
    label: string;
    badge: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  PASS: {
    label: "PASS",
    badge: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800",
    icon: CheckCircle2,
  },
  FAIL: {
    label: "FAIL",
    badge: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/80 dark:text-rose-300 dark:border-rose-800",
    icon: XCircle,
  },
  WARNING: {
    label: "WARNING",
    badge: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800",
    icon: AlertTriangle,
  },
  NOT_APPLICABLE: {
    label: "N/A",
    badge: "bg-slate-100 text-slate-600 border-slate-300 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
    icon: HelpCircle,
  },
  INSUFFICIENT_DATA: {
    label: "INSUFFICIENT",
    badge: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/80 dark:text-orange-300 dark:border-orange-800",
    icon: AlertTriangle,
  },
  NEEDS_EXPERT_REVIEW: {
    label: "EXPERT REVIEW",
    badge: "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-950/80 dark:text-purple-300 dark:border-purple-800",
    icon: AlertTriangle,
  },
  NOT_YET_TESTED: {
    label: "PENDING",
    badge: "bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-900 dark:text-slate-500 dark:border-slate-800",
    icon: Clock,
  },
};

export const LayerPipelineMatrix: React.FC<LayerPipelineMatrixProps> = ({
  layers = {},
  className = "",
}) => {
  const [expandedLayers, setExpandedLayers] = useState<Record<number, boolean>>({});

  const toggleLayer = (layerNum: number) => {
    setExpandedLayers((prev) => ({
      ...prev,
      [layerNum]: !prev[layerNum],
    }));
  };

  return (
    <div
      data-testid="layer-pipeline-matrix"
      className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 overflow-hidden ${className}`}
    >
      <div className="border-b border-slate-200 bg-slate-50/75 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
            Validation Findings by Layer
          </h3>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
          Layer definitions follow project requirements
        </span>
      </div>

      <div className="divide-y divide-slate-200 dark:divide-slate-800">
        {[1, 2, 3, 4, 5, 6].map((layerNum) => {
          const finding: LayerFinding | undefined = layers[layerNum];
          const meta = LAYER_METADATA[layerNum];
          const LayerIcon = meta.icon;
          const state: FindingState = finding ? finding.state : "NOT_YET_TESTED";
          const stateStyle = STATE_STYLES[state] || STATE_STYLES.NOT_YET_TESTED;
          const StateIcon = stateStyle.icon;
          const isExpanded = !!expandedLayers[layerNum];
          const hasDetails =
            finding &&
            ((finding.diagnostics && finding.diagnostics.length > 0) ||
              finding.details ||
              finding.message);

          return (
            <div
              key={layerNum}
              className="p-3 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-900/25"
            >
              <div
                className="flex items-center justify-between gap-3 cursor-pointer select-none"
                onClick={() => hasDetails && toggleLayer(layerNum)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 flex-shrink-0">
                    <LayerIcon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-slate-900 dark:text-slate-100">
                        {finding ? finding.name : meta.title}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {finding ? finding.message : meta.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${stateStyle.badge}`}
                  >
                    <StateIcon className="w-3.5 h-3.5" />
                    {stateStyle.label}
                  </span>

                  {hasDetails && (
                    <button
                      type="button"
                      aria-label="Toggle details"
                      className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {isExpanded && finding && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-850 pl-11 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-mono text-slate-600 dark:text-slate-400">
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      Diagnostic Code:
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                      {finding.diagnostic_code}
                    </span>
                  </div>

                  {finding.diagnostics && finding.diagnostics.length > 0 && (
                    <div className="space-y-1">
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        Diagnostics:
                      </span>
                      <ul className="list-disc pl-4 space-y-0.5 text-slate-600 dark:text-slate-400">
                        {finding.diagnostics.map((diag, i) => (
                          <li key={i}>{diag}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {finding.details && (
                    <div className="space-y-1">
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        Evaluation Payload:
                      </span>
                      <pre className="p-2 rounded bg-slate-100 dark:bg-slate-900 font-mono text-[11px] overflow-x-auto text-slate-800 dark:text-slate-300">
                        {JSON.stringify(finding.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
