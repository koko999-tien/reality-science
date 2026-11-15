"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Variable,
  Workflow,
  ShieldCheck,
  FileArchive,
  ArrowRight,
  CheckCircle2,
  Atom,
  Binary,
  Code,
  FileCode,
  Sparkles,
} from "lucide-react";

export interface WorkflowStep {
  stepNumber: string;
  stepIndex: number;
  id: string;
  title: string;
  tagline: string;
  icon: React.ReactNode;
  description: string;
  capabilities: string[];
  mockupType: "variables" | "canvas" | "verification" | "bundle";
}

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    stepNumber: "STEP 01",
    stepIndex: 1,
    id: "step-declare-quantities",
    title: "Declare Physical Quantities & Pint Units",
    tagline: "Typed dimensional foundations for physical reality",
    icon: <Variable className="h-5 w-5 text-cyan-400" />,
    description:
      "Every mathematical symbol begins with physical grounding. Define symbols, descriptive names, domain constraints (positive real, real, integer), and exact Pint SI dimensional units ([M], [L], [T], [Q]) before equation synthesis.",
    capabilities: [
      "Symbol-first physical quantity manifest",
      "Strict Pint SI unit dimensional typing",
      "Mathematical domain constraints (positive real, non-zero)",
      "Automated dimensional basis reduction",
    ],
    mockupType: "variables",
  },
  {
    stepNumber: "STEP 02",
    stepIndex: 2,
    id: "step-compose-canvas",
    title: "Compose Equation Nodes on Symbolic Canvas",
    tagline: "Visual node-based AST DAG construction",
    icon: <Workflow className="h-5 w-5 text-violet-400" />,
    description:
      "Construct scientific models visually without syntax errors. Connect constants, declared physical variables, binary operators (+, -, *, /, **), and function calls into an acyclic dataflow graph with live KaTeX rendering.",
    capabilities: [
      "Visual node-based dataflow powered by @xyflow/react",
      "Bidirectional AST <-> graph synchronization",
      "Live KaTeX typesetting on node handles and equation root",
      "Automated hierarchical DAG layout and depth validation",
    ],
    mockupType: "canvas",
  },
  {
    stepNumber: "STEP 03",
    stepIndex: 3,
    id: "step-execute-verification",
    title: "Execute 6-Layer Multi-Stage Truth Verification",
    tagline: "Automated epistemic verification against physical laws",
    icon: <ShieldCheck className="h-5 w-5 text-emerald-400" />,
    description:
      "Submit the AST to the ADR-001 zero-trust compute sandbox. The Reality Constraint Engine systematically validates syntax limits, asymptotic boundaries, Pint SI homogeneity, Noether symmetries, empirical datasets, and epistemic DAG acyclicity.",
    capabilities: [
      "Sub-15ms multi-stage evaluation pipeline",
      "Pint SI dimensional homogeneity theorem proving",
      "SymPy asymptotic singularity and branch cut detection",
      "Acyclic epistemic DAG validation via Tarjan SCC",
    ],
    mockupType: "verification",
  },
  {
    stepNumber: "STEP 04",
    stepIndex: 4,
    id: "step-export-bundle",
    title: "Export Cryptographically Signed Preprint Bundle",
    tagline: "Tamper-evident, audit-ready scientific reproducibility",
    icon: <FileArchive className="h-5 w-5 text-amber-400" />,
    description:
      "Generate an immutable, self-contained verification package with a single click. Packages include canonical AST JSON, full execution logs, SHA-256 digests, and preprint evidence manifests ready for publication.",
    capabilities: [
      "Single-click ZIP archive export via JSZip",
      "SHA-256 cryptographic provenance for AST and execution logs",
      "Preprint-ready Markdown & JSON-LD evidence artifacts",
      "100% reproducible independent re-verification",
    ],
    mockupType: "bundle",
  },
];

export const WorkflowTour: React.FC = () => {
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);

  const activeStep = WORKFLOW_STEPS[activeStepIndex];

  return (
    <section className="relative py-12 sm:py-16">
      {/* Section Header */}
      <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-14">
        <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-950/40 px-3 py-1 shadow-sm mb-3">
          <Sparkles className="h-3.5 w-3.5 text-violet-400" />
          <span className="text-xs font-mono font-medium text-violet-300 uppercase tracking-widest">
            Scientific Methodology
          </span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
          From Intuition to Mathematically Proven Reality
        </h2>
        <p className="text-sm sm:text-base text-slate-400 mt-3 max-w-2xl mx-auto leading-relaxed">
          Follow the four-step scientific research workflow designed to eliminate dimensional errors, prevent
          mathematical singularities, and prove epistemic consistency.
        </p>
      </div>

      {/* Main Workflow Container */}
      <div className="rounded-2xl border border-white/10 bg-slate-950/70 backdrop-blur-2xl p-4 sm:p-8 shadow-2xl">
        {/* Step Navigation Tabs */}
        <div
          role="tablist"
          aria-label="Workflow step navigation"
          className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 p-1.5 rounded-xl bg-slate-900/80 border border-white/10 mb-8"
        >
          {WORKFLOW_STEPS.map((step, idx) => {
            const isActive = idx === activeStepIndex;

            return (
              <button
                key={step.id}
                role="tab"
                aria-selected={isActive}
                aria-controls={`workflow-panel-${step.id}`}
                onClick={() => setActiveStepIndex(idx)}
                className={`flex flex-col sm:flex-row items-start sm:items-center gap-2.5 p-3 rounded-lg text-left transition-all duration-200 ${
                  isActive
                    ? "bg-slate-800 text-white border border-cyan-500/40 shadow-md shadow-cyan-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent"
                }`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${
                    isActive
                      ? "bg-cyan-950 border-cyan-500/50 text-cyan-300"
                      : "bg-slate-900 border-white/10 text-slate-400"
                  }`}
                >
                  {step.icon}
                </div>
                <div className="overflow-hidden">
                  <span
                    className={`block text-[10px] font-mono font-bold tracking-wider uppercase ${
                      isActive ? "text-cyan-400" : "text-slate-500"
                    }`}
                  >
                    {step.stepNumber}
                  </span>
                  <span className="block text-xs font-semibold truncate text-slate-200">{step.title}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Active Step Content Grid */}
        <div
          id={`workflow-panel-${activeStep.id}`}
          className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-center"
        >
          {/* Left Column: Step Description & Capabilities */}
          <div className="lg:col-span-6 space-y-5">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-mono">
                <span>{activeStep.stepNumber}</span>
                <span>·</span>
                <span>{activeStep.tagline}</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mt-3">{activeStep.title}</h3>
              <p className="text-sm text-slate-300 mt-2 leading-relaxed">{activeStep.description}</p>
            </div>

            {/* Key Capabilities list */}
            <div className="space-y-2.5 pt-4 border-t border-white/10">
              <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider block">
                Technical Capabilities:
              </span>
              {activeStep.capabilities.map((cap, cIdx) => (
                <div key={cIdx} className="flex items-center gap-2 text-xs text-slate-200">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0" />
                  <span>{cap}</span>
                </div>
              ))}
            </div>

            {/* Navigation Buttons */}
            <div className="flex items-center gap-3 pt-4">
              <button
                onClick={() => setActiveStepIndex((prev) => (prev + 1) % WORKFLOW_STEPS.length)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-xs font-medium text-white transition-colors"
              >
                <span>Next Step</span>
                <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
              </button>
              <Link
                href="/projects/default-model/editor"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white shadow-md shadow-cyan-600/20 transition-all"
              >
                <span>Open Symbolic Canvas</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {/* Right Column: Live Interactive Mockup / Telemetry Preview */}
          <div className="lg:col-span-6">
            <div className="rounded-xl border border-white/10 bg-slate-900/90 backdrop-blur-xl p-5 shadow-inner space-y-4">
              {/* Window Controls Bar */}
              <div className="flex items-center justify-between pb-3 border-b border-white/10 text-xs font-mono text-slate-400">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono ml-2">reality_science_studio.rce</span>
                </div>
                <span className="text-[10px] text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                  {activeStep.stepNumber}
                </span>
              </div>

              {/* Dynamic Step-Specific Interactive Mockup */}
              {activeStep.mockupType === "variables" && (
                <div data-testid="mockup-variables" className="space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400">Physical Variable Manifest (Pint SI):</div>
                  <div className="space-y-2">
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-cyan-500/30 flex items-center justify-between">
                      <div>
                        <span className="text-cyan-300 font-bold">m</span>
                        <span className="text-slate-400 ml-2">Rest Mass</span>
                      </div>
                      <span className="text-slate-300 text-[11px] bg-slate-800 px-2 py-0.5 rounded">kilogram [M]</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-cyan-500/30 flex items-center justify-between">
                      <div>
                        <span className="text-cyan-300 font-bold">c</span>
                        <span className="text-slate-400 ml-2">Speed of Light</span>
                      </div>
                      <span className="text-slate-300 text-[11px] bg-slate-800 px-2 py-0.5 rounded">
                        meter / second [L][T]^-1
                      </span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-white/10 flex items-center justify-between opacity-80">
                      <div>
                        <span className="text-violet-300 font-bold">E</span>
                        <span className="text-slate-400 ml-2">Rest Energy</span>
                      </div>
                      <span className="text-slate-300 text-[11px] bg-slate-800 px-2 py-0.5 rounded">
                        joule [M][L]^2[T]^-2
                      </span>
                    </div>
                  </div>
                  <div className="text-[10px] text-emerald-400 flex items-center gap-1.5 pt-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>All 3 physical dimensions validated against SI base standard.</span>
                  </div>
                </div>
              )}

              {activeStep.mockupType === "canvas" && (
                <div data-testid="mockup-canvas" className="space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400">Reactive AST Node Graph Flow:</div>
                  <div className="p-4 rounded-xl bg-slate-950/90 border border-violet-500/30 relative flex flex-col items-center justify-center gap-3 py-6">
                    <div className="flex items-center gap-4">
                      <div className="px-3 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-[11px]">
                        Variable Node [m]
                      </div>
                      <span className="text-slate-500">→</span>
                      <div className="px-3 py-1.5 rounded-lg bg-amber-950/80 border border-amber-500/40 text-amber-300 text-[11px]">
                        BinaryOp [*]
                      </div>
                      <span className="text-slate-500">→</span>
                      <div className="px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-[11px]">
                        Equation Root [E]
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 text-[10px]">
                      <span>└─ Constant Node [c²] (Handle right) ─┘</span>
                    </div>
                  </div>
                  <div className="text-[10px] text-cyan-400 flex items-center justify-between">
                    <span>AST Depth: 2 / 15</span>
                    <span>Node Count: 4 / 100</span>
                    <span className="text-emerald-400">Acyclic Verified</span>
                  </div>
                </div>
              )}

              {activeStep.mockupType === "verification" && (
                <div data-testid="mockup-verification" className="space-y-2.5 font-mono text-xs">
                  <div className="text-[11px] text-slate-400">6-Layer Reality Constraint Matrix:</div>
                  <div className="space-y-1.5">
                    {[
                      { l: 1, name: "AST Syntax & Complexity", status: "PASS", time: "1.2ms" },
                      { l: 2, name: "Boundary Asymptotics", status: "PASS", time: "2.4ms" },
                      { l: 3, name: "Pint SI Homogeneity", status: "PASS", time: "3.1ms" },
                      { l: 4, name: "Noether Invariants", status: "PASS", time: "1.8ms" },
                      { l: 5, name: "Empirical Correlation", status: "PASS", time: "2.0ms" },
                      { l: 6, name: "Epistemic Logic DAG", status: "PASS", time: "1.5ms" },
                    ].map((row) => (
                      <div
                        key={row.l}
                        className="px-2.5 py-1.5 rounded bg-slate-950/70 border border-emerald-500/20 flex items-center justify-between text-[11px]"
                      >
                        <span className="text-slate-300">
                          Layer {row.l}: {row.name}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-500">{row.time}</span>
                          <span className="text-emerald-400 font-bold flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> {row.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeStep.mockupType === "bundle" && (
                <div data-testid="mockup-bundle" className="space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400">Cryptographic Verification Manifest:</div>
                  <div className="p-3 rounded-lg bg-slate-950/90 border border-amber-500/30 space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-amber-300 font-bold flex items-center gap-1.5">
                        <FileArchive className="h-4 w-4" />
                        verification_bundle_v1.zip
                      </span>
                      <span className="text-slate-400">14.8 KB</span>
                    </div>
                    <div className="text-[10px] text-slate-400 break-all bg-slate-900 p-2 rounded border border-white/5">
                      <span className="text-slate-500 block mb-0.5">SHA-256 Digest:</span>
                      <span className="text-cyan-300">
                        e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                      <span>• canonical_ast.json</span>
                      <span>• telemetry_log.json</span>
                      <span>• proof_manifest.md</span>
                    </div>
                  </div>
                  <div className="text-[10px] text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Cryptographically verified &amp; audit-ready for preprint submission.</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
