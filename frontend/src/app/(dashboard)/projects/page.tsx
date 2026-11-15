import React from "react";
import Link from "next/link";
import { Layers, Sparkles, ShieldCheck, ArrowRight, Atom, Plus, Activity } from "lucide-react";

interface ProjectItem {
  slug: string;
  title: string;
  category: string;
  status: "Verified" | "Draft" | "Validating";
  dimension: string;
  description: string;
  layerCoverage: string;
}

const RESEARCH_PROJECTS: ProjectItem[] = [
  {
    slug: "dark-matter-particle",
    title: "Dark Matter Particle Cross-Section",
    category: "Astroparticle Physics",
    status: "Draft",
    dimension: "[L]^2",
    description: "Astrophysical null result constraints evaluated against Xenon-1T and LUX-ZEPLIN dataset benchmarks.",
    layerCoverage: "6 Layers Active",
  },
  {
    slug: "kinematics-velocity",
    title: "Kinematic Acceleration Dynamics",
    category: "Classical Mechanics",
    status: "Verified",
    dimension: "[L] [T]^{-1}",
    description: "Classical and relativistic velocity summation with strict Pint SI dimensional homogeneity verification.",
    layerCoverage: "6/6 Layers PASS",
  },
  {
    slug: "einstein-energy",
    title: "Einstein Mass-Energy Equivalence",
    category: "Special Relativity",
    status: "Verified",
    dimension: "[M] [L]^2 [T]^{-2}",
    description: "Lorentz-Poincaré tensor conservation E = mc^2 verified against Noether 4-momentum conservation laws.",
    layerCoverage: "6/6 Layers PASS",
  },
  {
    slug: "newtonian-gravity",
    title: "Newtonian Celestial Gravitation",
    category: "Astrophysics",
    status: "Verified",
    dimension: "[M] [L] [T]^{-2}",
    description: "Inverse-square law orbital dynamics evaluated against Solar System planetary ephemeris benchmarks.",
    layerCoverage: "6/6 Layers PASS",
  },
];

export default function ProjectsDashboardPage() {
  return (
    <div className="container mx-auto p-6 sm:p-8 space-y-8 max-w-7xl">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">
            <Layers className="h-4 w-4" />
            <span>Epistemic Model Catalog</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            Scientific Research Models
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Manage mathematical models, active hypothesis versions, and 6-layer reality constraint runs.
          </p>
        </div>

        <Link
          href="/projects/default-model/editor"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 px-4 py-2.5 text-xs font-semibold text-white shadow-tactile-card border border-cyan-400/40 transition-all active:scale-[0.98]"
        >
          <Plus className="h-4 w-4" />
          <span>New Mathematical Model</span>
        </Link>
      </div>

      {/* Model Cards Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-2">
        {RESEARCH_PROJECTS.map((project) => (
          <div
            key={project.slug}
            className="group relative rounded-2xl border border-white/[0.08] bg-slate-900/80 backdrop-blur-xl p-6 shadow-tactile-card hover:border-white/20 transition-all duration-300 flex flex-col justify-between"
          >
            {/* Top highlight */}
            <div className="flex items-center justify-between gap-3 mb-3">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                <Atom className="h-3 w-3 text-cyan-400" />
                {project.category}
              </span>

              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/70 border border-cyan-800/60 px-2 py-0.5 rounded">
                  {project.dimension}
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    project.status === "Verified"
                      ? "bg-emerald-950/70 text-emerald-400 border-emerald-800/60"
                      : "bg-amber-950/70 text-amber-300 border-amber-800/60"
                  }`}
                >
                  {project.status}
                </span>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                {project.title}
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
                {project.description}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                {project.layerCoverage}
              </span>

              <Link
                href={`/projects/${project.slug}/editor`}
                className="inline-flex items-center gap-1 font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                <span>Launch Studio</span>
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
