import React from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  Layers,
  Atom,
  Github,
  ExternalLink,
} from "lucide-react";
import { ScientificPresetDemo } from "@/components/home/ScientificPresetDemo";
import { FeaturePillars } from "@/components/home/FeaturePillars";
import { WorkflowTour } from "@/components/home/WorkflowTour";
import { KineticParticleField } from "@/components/canvas/KineticParticleField";

export default function HomePage() {
  return (
    <div className="relative min-h-screen bg-[#030712] text-slate-100 overflow-hidden selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Precision Laboratory Coordinate Grid & Collimated Spotlight Substrate */}
      <div
        className="pointer-events-none absolute inset-0 bg-lab-grid bg-[size:48px_48px] opacity-[0.22] -z-20"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[640px] bg-radial-spotlight -z-20"
        aria-hidden="true"
      />

      {/* Hero Section with Living Kinetic Particle Field */}
      <section className="relative pt-12 sm:pt-20 pb-12 sm:pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <KineticParticleField density={1.2} interactive={true} equationModulation={true} />

        {/* Laboratory Coordinate Crosshairs */}
        <span className="pointer-events-none absolute top-8 left-8 text-xs font-mono text-white/20 select-none" aria-hidden="true">+</span>
        <span className="pointer-events-none absolute top-8 right-8 text-xs font-mono text-white/20 select-none" aria-hidden="true">+</span>

        <div className="text-center space-y-6 max-w-4xl mx-auto relative z-10">
          {/* Status Badge */}
          <div className="inline-flex items-center gap-2.5 rounded-full border border-cyan-500/30 bg-slate-900/90 backdrop-blur-md px-4 py-1.5 shadow-tactile-card">
            <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            <span className="text-xs font-mono font-semibold text-cyan-300 tracking-wide">
              ⚡ Epistemic Physics &amp; Mathematical Verification Engine v1.0
            </span>
            <span className="hidden sm:inline-block text-[11px] font-mono text-emerald-400 border-l border-white/10 pl-2">
              🟢 Systems Operational — 6-Layer RCE Online
            </span>
          </div>

          {/* Main Title & Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-tight">
            REALITY{" "}
            <span className="text-cyan-400 drop-shadow-[0_0_28px_rgba(14,165,233,0.35)]">
              SCIENCE
            </span>
            <span className="block text-xl sm:text-2xl md:text-3xl font-semibold text-slate-300 mt-4 font-sans tracking-normal">
              Mathematically Rigorous Hypothesis &amp; Reality Constraint Engine
            </span>
          </h1>

          {/* Subtitle & Mission Statement */}
          <p className="text-base sm:text-lg text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Evidence-Driven Scientific Hypothesis &amp; Mathematical Verification Engine.
            Bridge theoretical equations and physical reality through multi-node AST dataflow modeling, Pint SI
            dimensional verification, and 6-layer truth validation.
          </p>

          {/* Primary & Secondary Call to Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2">
            <Link
              href="/projects/default-model/editor"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 px-7 py-3.5 text-sm sm:text-base font-bold text-white shadow-tactile-card border border-cyan-400/40 transition-all duration-200 transform hover:-translate-y-0.5 active:scale-[0.98]"
            >
              <Sparkles className="h-4 w-4" />
              <span>Launch Studio Canvas</span>
              <ArrowRight className="h-4 w-4 ml-0.5" />
            </Link>

            <Link
              href="/projects"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-slate-900/80 hover:bg-slate-800/90 hover:border-white/30 px-6 py-3.5 text-sm sm:text-base font-semibold text-slate-200 transition-all duration-200 shadow-tactile-card active:scale-[0.98]"
            >
              <Layers className="h-4 w-4 text-slate-400" />
              <span>Browse Model Catalog</span>
            </Link>
          </div>

          {/* Quick Metrics Bar */}
          <div className="pt-8 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto text-left">
            <div className="p-3.5 rounded-xl border border-white/[0.08] bg-slate-900/70 backdrop-blur-md shadow-tactile-card">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Verification Depth</div>
              <div className="text-lg font-bold text-cyan-400 mt-0.5 font-mono">6 Axiomatic Layers</div>
            </div>
            <div className="p-3.5 rounded-xl border border-white/[0.08] bg-slate-900/70 backdrop-blur-md shadow-tactile-card">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Sandbox Isolation</div>
              <div className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">ADR-001 Air-Gapped</div>
            </div>
            <div className="p-3.5 rounded-xl border border-white/[0.08] bg-slate-900/70 backdrop-blur-md shadow-tactile-card">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Dimensional Typing</div>
              <div className="text-lg font-bold text-violet-400 mt-0.5 font-mono">100+ Pint SI Units</div>
            </div>
            <div className="p-3.5 rounded-xl border border-white/[0.08] bg-slate-900/70 backdrop-blur-md shadow-tactile-card">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Preflight Latency</div>
              <div className="text-lg font-bold text-amber-400 mt-0.5 font-mono">&lt; 5 ms Cached</div>
            </div>
          </div>
        </div>

        {/* Embedded Interactive 1-Click Preset Demo Widget */}
        <div className="mt-12 sm:mt-16 relative z-10">
          <ScientificPresetDemo />
        </div>
      </section>

      {/* 4 Feature Pillars Section */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto relative z-10">
        <FeaturePillars />
      </section>

      {/* 4-Step Scientific Workflow Tour Section */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto relative z-10">
        <WorkflowTour />
      </section>

      {/* Bottom High-Conversion Banner */}
      <section className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto relative z-10">
        <div className="rounded-3xl border border-cyan-500/30 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-8 sm:p-12 text-center relative overflow-hidden shadow-2xl">
          <div
            className="absolute inset-0 bg-radial-gradient from-cyan-500/10 via-transparent to-transparent pointer-events-none"
            aria-hidden="true"
          />

          <div className="relative z-10 max-w-2xl mx-auto space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/40 bg-cyan-950/60 px-3.5 py-1 text-xs font-mono text-cyan-300">
              <Atom className="h-3.5 w-3.5 animate-spin" style={{ animationDuration: "12s" }} />
              <span>Autonomous Scientific RCE Studio</span>
            </div>

            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ready to Test Your Mathematical Hypothesis Against Reality?
            </h2>

            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Step into the interactive visual DAG canvas, declare your physical variables with strict Pint SI units,
              and prove dimensional invariance with sub-15ms automated verification.
            </p>

            <div className="pt-2">
              <Link
                href="/projects/default-model/editor"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 px-8 py-4 text-base font-bold text-white shadow-tactile-card border border-cyan-400/40 transition-all duration-200 transform hover:-translate-y-0.5 active:scale-[0.98]"
              >
                <span>Open Verification Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Futuristic High-Tech Footer */}
      <footer className="border-t border-white/10 bg-slate-950/90 text-slate-400 py-12 px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-7xl mx-auto space-y-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            {/* Brand Logo & Mission */}
            <div className="space-y-2 max-w-md">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                  <Atom className="h-4 w-4 text-cyan-400" />
                </div>
                <span className="text-base font-extrabold text-white tracking-wider">
                  REALITY<span className="text-cyan-400">SCIENCE</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Autonomous Epistemic Verification Studio for evaluating physical hypotheses against axiomatic ground truth.
              </p>
            </div>

            {/* Quick Links & GitHub */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-medium">
              <Link
                href="/projects/default-model/editor"
                className="text-slate-300 hover:text-cyan-400 transition-colors"
              >
                Canvas Editor
              </Link>
              <Link href="/projects" className="text-slate-300 hover:text-cyan-400 transition-colors">
                Model Catalog
              </Link>
              <a
                href="https://github.com/TienNguyenD/Reality_Science"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-slate-300 hover:text-white transition-colors"
              >
                <Github className="h-4 w-4" />
                <span>GitHub Repository</span>
                <ExternalLink className="h-3 w-3 text-slate-500" />
              </a>
            </div>
          </div>

          {/* Developer API & Architecture Disclaimer */}
          <div className="p-4 rounded-xl border border-white/5 bg-slate-900/40 text-[11px] leading-relaxed text-slate-400 font-mono">
            <span className="text-cyan-400 font-semibold uppercase block mb-1">Developer &amp; Headless API Note:</span>
            The Reality Science backend provides headless RCE execution via programmatic REST endpoints (/api/v1) for
            automated CI/CD pipelines, cluster orchestration, and headless verification scripts. For researchers,
            interactive mathematical modeling, and visual DAG equation construction, use the Web Studio Canvas interface.
          </div>

          {/* Copyright & License */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/5 text-xs text-slate-500 font-mono">
            <div>
              &copy; {new Date().getFullYear()} REALITY SCIENCE. MIT Open Source License.
            </div>
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span>Deployed on Vercel Edge Runtime · Next.js 15 App Router</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
