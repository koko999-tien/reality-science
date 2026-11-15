"use client";

import React from "react";
import {
  Layers,
  ShieldCheck,
  Share2,
  PackageCheck,
  Check,
  Cpu,
  Lock,
  Workflow,
  FileCheck2,
  Sparkles,
} from "lucide-react";

export interface FeaturePillarItem {
  id: string;
  pillarNumber: string;
  title: string;
  tagline: string;
  badge: string;
  icon: React.ReactNode;
  accentColor: "cyan" | "emerald" | "violet" | "amber";
  description: string;
  capabilities: { title: string; description: string }[];
  technicalSpecs: { label: string; value: string }[];
}

export const FEATURE_PILLARS: FeaturePillarItem[] = [
  {
    id: "pillar-6-layer",
    pillarNumber: "PILLAR 01",
    title: "6-Layer Epistemic Verification Pipeline",
    tagline: "Formal multi-stage mathematical constraint evaluation",
    badge: "Multi-Stage Truth Engine",
    icon: <Layers className="h-6 w-6 text-cyan-400" />,
    accentColor: "cyan",
    description:
      "Every scientific hypothesis undergoes an automated 6-stage gauntlet verifying syntax bounds, asymptotic singularities, Pint SI dimensional homogeneity, conserved physical Noether invariants, empirical benchmark correlation, and acyclic epistemic DAG consistency.",
    capabilities: [
      {
        title: "AST Syntax & Complexity Guard",
        description: "Enforces max AST tree depth <= 15 and max node count <= 100 to prevent DOS & cyclic expansion.",
      },
      {
        title: "Boundary Asymptotics & Singularity Detection",
        description: "Evaluates symbolic limits at zero, infinity, and pole boundaries via SymPy limit analysis.",
      },
      {
        title: "Pint SI Dimensional Homogeneity",
        description: "Strict algebraic dimensional verification across 100+ fundamental and derived Pint physical units.",
      },
      {
        title: "Physical Law Invariants & Noether Symmetry",
        description: "Verifies energy-momentum conservation, Galilean/Lorentz invariance, and thermodynamic bounds.",
      },
      {
        title: "Empirical Dataset Correlation",
        description: "Chi-square and R^2 regression testing against published physical benchmark repositories.",
      },
      {
        title: "Epistemic Logic DAG Consistency",
        description: "Tarjan strongly connected components (SCC) analysis to ensure acyclic, contradiction-free theory DAGs.",
      },
    ],
    technicalSpecs: [
      { label: "Verification Latency", value: "< 12 ms" },
      { label: "Dimensional Coverage", value: "100+ Pint Units" },
      { label: "Axiomatic Engine", value: "SymPy + Pint Core" },
    ],
  },
  {
    id: "pillar-zero-trust",
    pillarNumber: "PILLAR 02",
    title: "ADR-001 Zero-Trust Compute Isolation",
    tagline: "Pure mathematical evaluation in isolated sandboxes",
    badge: "Air-Gapped Security Architecture",
    icon: <ShieldCheck className="h-6 w-6 text-emerald-400" />,
    accentColor: "emerald",
    description:
      "Mathematical execution is strictly decoupled from state storage. Worker sandboxes execute pure mathematical AST reductions in ephemeral, memory-bounded micro-containers with zero database credentials or network access.",
    capabilities: [
      {
        title: "Zero Database Credentials in Worker",
        description: "Compute runners never hold DB credentials; all inputs arrive as immutable JSON AST payloads.",
      },
      {
        title: "Deterministic Execution Timeouts",
        description: "Strict 10-second hard wall-clock kill timeout per equation evaluation prevents runaway computation.",
      },
      {
        title: "Read-Only Memory Sandboxing",
        description: "Resource-limited worker threads prevent state leakage, filesystem mutations, or cross-tenant contamination.",
      },
      {
        title: "Air-Gapped Telemetry Logging",
        description: "Audit trails stream structured JSON diagnostic events back to the coordinator without persistence coupling.",
      },
    ],
    technicalSpecs: [
      { label: "Isolation Protocol", value: "ADR-001 Air-Gap" },
      { label: "Max Memory Footprint", value: "256 MB / sandbox" },
      { label: "Database Access", value: "0 Credentials (Strict)" },
    ],
  },
  {
    id: "pillar-flow-canvas",
    pillarNumber: "PILLAR 03",
    title: "Reactive AST Flow Canvas",
    tagline: "Interactive node-based DAG builder with live KaTeX rendering",
    badge: "Symbolic Visual Modeling",
    icon: <Workflow className="h-6 w-6 text-violet-400" />,
    accentColor: "violet",
    description:
      "Build complex scientific formulas visually with an intuitive flow canvas. Drag and wire constants, declared physical variables, binary operators, and transcendental functions with instant bidirectional AST synchronization and live KaTeX typography.",
    capabilities: [
      {
        title: "Bidirectional Graph <-> AST Sync",
        description: "Visual node DAG automatically compiles into canonical JSON AST representations and vice versa in real time.",
      },
      {
        title: "Live KaTeX Math Rendering",
        description: "Instant typesetting of mathematical formulas as you connect handles, powered by KaTeX typesetting.",
      },
      {
        title: "Pulsing Animated Photon Edges",
        description: "Glowing SVG connection paths with gradient pulses and moving photons indicate computational dataflow.",
      },
      {
        title: "SymPy Code Serialization",
        description: "Export visual node graphs directly into clean, executable SymPy Python equations with a single click.",
      },
    ],
    technicalSpecs: [
      { label: "Canvas Engine", value: "@xyflow/react v12" },
      { label: "Math Typography", value: "KaTeX 0.16" },
      { label: "Sync Latency", value: "< 4 ms React 19" },
    ],
  },
  {
    id: "pillar-crypto-bundles",
    pillarNumber: "PILLAR 04",
    title: "Cryptographic Verification Bundles",
    tagline: "Tamper-evident ZIP export containing AST, logs, and SHA-256 manifests",
    badge: "Audit-Ready Provenance",
    icon: <PackageCheck className="h-6 w-6 text-amber-400" />,
    accentColor: "amber",
    description:
      "Export reproducible, self-contained scientific verification archives. Bundles contain canonical AST JSON, execution logs, SHA-256 digests, and epistemic proof manifests ready for peer-review preprint inclusion or archival replication.",
    capabilities: [
      {
        title: "Self-Contained ZIP Export",
        description: "Single-click download bundling all model specifications, variable definitions, and validation telemetry.",
      },
      {
        title: "SHA-256 Cryptographic Hashes",
        description: "Every equation AST and execution log is hashed with SHA-256 to guarantee immutable, tamper-evident lineage.",
      },
      {
        title: "Preprint Evidence Manifest",
        description: "Structured JSON and Markdown summaries designed for arXiv and journal supplementary material submission.",
      },
      {
        title: "Instant Re-Verification",
        description: "Any researcher can drag a bundle into the Canvas Studio to reproduce the exact 6-layer verification result.",
      },
    ],
    technicalSpecs: [
      { label: "Packaging Format", value: "PKWare ZIP (JSZip)" },
      { label: "Digest Standard", value: "SHA-256 Cryptographic" },
      { label: "Audit Format", value: "JSON-LD & Markdown" },
    ],
  },
];

export const FeaturePillars: React.FC = () => {
  return (
    <section className="relative py-12 sm:py-16">
      <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3 py-1 shadow-sm mb-3">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-xs font-mono font-medium text-cyan-300 uppercase tracking-widest">
            Core Architecture
          </span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
          Engineered for Mathematical Truth &amp; Physical Rigor
        </h2>
        <p className="text-sm sm:text-base text-slate-400 mt-3 max-w-2xl mx-auto leading-relaxed">
          Four foundational pillars combine symbolic AST execution, air-gapped security, and cryptographic provenance
          into an uncompromising scientific research platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
        {FEATURE_PILLARS.map((pillar) => {
          const isCyan = pillar.accentColor === "cyan";
          const isEmerald = pillar.accentColor === "emerald";
          const isViolet = pillar.accentColor === "violet";
          const isAmber = pillar.accentColor === "amber";

          return (
            <div
              key={pillar.id}
              data-testid={`feature-pillar-${pillar.id}`}
              className="group relative rounded-2xl border border-white/[0.08] bg-slate-900/80 backdrop-blur-xl p-6 sm:p-8 hover:border-white/20 transition-all duration-300 flex flex-col justify-between shadow-tactile-card"
            >
              {/* Corner Coordinate Crosshair */}
              <span className="pointer-events-none absolute top-3 right-3 text-[10px] font-mono text-white/15 select-none" aria-hidden="true">+</span>

              {/* Subtle accent hover glow overlay */}
              <div
                className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none -z-10 ${
                  isCyan
                    ? "bg-gradient-to-br from-cyan-500/10 via-transparent to-transparent"
                    : isEmerald
                    ? "bg-gradient-to-br from-emerald-500/10 via-transparent to-transparent"
                    : isViolet
                    ? "bg-gradient-to-br from-violet-500/10 via-transparent to-transparent"
                    : "bg-gradient-to-br from-amber-500/10 via-transparent to-transparent"
                }`}
              />

              <div>
                {/* Header Row */}
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-12 w-12 items-center justify-center rounded-xl border transition-transform duration-300 group-hover:scale-105 ${
                        isCyan
                          ? "bg-cyan-950/60 border-cyan-500/40 text-cyan-400"
                          : isEmerald
                          ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-400"
                          : isViolet
                          ? "bg-violet-950/60 border-violet-500/40 text-violet-400"
                          : "bg-amber-950/60 border-amber-500/40 text-amber-400"
                      }`}
                    >
                      {pillar.icon}
                    </div>
                    <div>
                      <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-slate-500">
                        {pillar.pillarNumber}
                      </span>
                      <div className="text-xs font-mono font-medium text-slate-400">{pillar.badge}</div>
                    </div>
                  </div>
                </div>

                {/* Pillar Title & Tagline */}
                <h3 className="text-lg sm:text-xl font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {pillar.title}
                </h3>
                <p className="text-xs sm:text-sm text-cyan-400/90 font-mono mt-1 font-medium">{pillar.tagline}</p>
                <p className="text-xs sm:text-sm text-slate-300 mt-3 leading-relaxed">{pillar.description}</p>

                {/* Capability Bullet Points */}
                <div className="mt-5 space-y-2.5 pt-4 border-t border-white/5">
                  {pillar.capabilities.slice(0, 3).map((cap, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs">
                      <div
                        className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${
                          isCyan
                            ? "bg-cyan-500/20 text-cyan-400"
                            : isEmerald
                            ? "bg-emerald-500/20 text-emerald-400"
                            : isViolet
                            ? "bg-violet-500/20 text-violet-400"
                            : "bg-amber-500/20 text-amber-400"
                        }`}
                      >
                        <Check className="h-2.5 w-2.5" />
                      </div>
                      <div className="leading-snug">
                        <span className="font-semibold text-white">{cap.title}: </span>
                        <span className="text-slate-400">{cap.description}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Technical Specs Footer Bar */}
              <div className="mt-6 pt-4 border-t border-white/10 grid grid-cols-3 gap-2 text-[11px] font-mono bg-slate-950/40 p-2.5 rounded-lg">
                {pillar.technicalSpecs.map((spec, sIdx) => (
                  <div key={sIdx} className="flex flex-col">
                    <span className="text-slate-500 uppercase text-[9px] truncate">{spec.label}</span>
                    <span className="text-slate-200 font-semibold truncate mt-0.5">{spec.value}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
