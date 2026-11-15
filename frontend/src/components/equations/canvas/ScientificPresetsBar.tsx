"use client";

import React, { useState } from "react";
import { VariableSpec, ExprNode } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { Sparkles, Atom, Orbit, Flame, Activity, Zap, ArrowRight } from "lucide-react";

export type PresetCategory = "Classical" | "Relativistic" | "Astrophysics" | "Thermodynamics" | "Oscillations";

export interface ScientificPreset {
  id: string;
  name: string;
  tagline: string;
  category: PresetCategory;
  formulaLatex: string;
  variables: VariableSpec[];
  ast: ExprNode;
}

export const CANONICAL_PRESETS: ScientificPreset[] = [
  {
    id: "kinematics",
    name: "Kinematics Velocity",
    tagline: "Linear velocity under constant acceleration",
    category: "Classical",
    formulaLatex: "v_0 + a \\cdot t",
    variables: [
      { symbol: "v_0", name: "Initial Velocity", unit: "meter / second", domain: "real", latex_presentation: "v_0" },
      { symbol: "a", name: "Acceleration", unit: "meter / second ** 2", domain: "real", latex_presentation: "a" },
      { symbol: "t", name: "Elapsed Time", unit: "second", domain: "positive_real", latex_presentation: "t" },
    ],
    ast: {
      node_type: "binary_op",
      op: "+",
      left: { node_type: "variable", value: "v_0" },
      right: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "variable", value: "a" },
        right: { node_type: "variable", value: "t" },
      },
    },
  },
  {
    id: "einstein-energy",
    name: "Einstein Mass-Energy",
    tagline: "Equivalence of relativistic mass and rest energy",
    category: "Relativistic",
    formulaLatex: "m \\cdot c^{2}",
    variables: [
      { symbol: "m", name: "Rest Mass", unit: "kilogram", domain: "positive_real", latex_presentation: "m" },
      { symbol: "c", name: "Speed of Light", unit: "meter / second", domain: "positive_real", latex_presentation: "c" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: { node_type: "variable", value: "m" },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "c" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "newton-gravity",
    name: "Newton's Gravity",
    tagline: "Universal gravitational attraction between masses",
    category: "Astrophysics",
    formulaLatex: "\\frac{G \\cdot (m_1 \\cdot m_2)}{r^{2}}",
    variables: [
      { symbol: "G", name: "Gravitational Constant", unit: "meter ** 3 / (kilogram * second ** 2)", domain: "positive_real", latex_presentation: "G" },
      { symbol: "m_1", name: "Mass 1", unit: "kilogram", domain: "positive_real", latex_presentation: "m_1" },
      { symbol: "m_2", name: "Mass 2", unit: "kilogram", domain: "positive_real", latex_presentation: "m_2" },
      { symbol: "r", name: "Radial Distance", unit: "meter", domain: "positive_real", latex_presentation: "r" },
    ],
    ast: {
      node_type: "binary_op",
      op: "/",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "variable", value: "G" },
        right: {
          node_type: "binary_op",
          op: "*",
          left: { node_type: "variable", value: "m_1" },
          right: { node_type: "variable", value: "m_2" },
        },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "r" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "kinetic-energy",
    name: "Kinetic Energy",
    tagline: "Work required to accelerate a body of mass m",
    category: "Classical",
    formulaLatex: "(0.5 \\cdot m) \\cdot v^{2}",
    variables: [
      { symbol: "m", name: "Mass", unit: "kilogram", domain: "positive_real", latex_presentation: "m" },
      { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real", latex_presentation: "v" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "constant", value: 0.5 },
        right: { node_type: "variable", value: "m" },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "v" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "ideal-gas",
    name: "Ideal Gas Law",
    tagline: "State of an ideal gas relating P, V, n, R, T",
    category: "Thermodynamics",
    formulaLatex: "\\frac{(n \\cdot R) \\cdot T}{V}",
    variables: [
      { symbol: "n", name: "Amount of Substance", unit: "mole", domain: "positive_real", latex_presentation: "n" },
      { symbol: "R", name: "Gas Constant", unit: "joule / (kelvin * mole)", domain: "positive_real", latex_presentation: "R" },
      { symbol: "T", name: "Absolute Temperature", unit: "kelvin", domain: "positive_real", latex_presentation: "T" },
      { symbol: "V", name: "Volume", unit: "meter ** 3", domain: "positive_real", latex_presentation: "V" },
    ],
    ast: {
      node_type: "binary_op",
      op: "/",
      left: {
        node_type: "binary_op",
        op: "*",
        left: {
          node_type: "binary_op",
          op: "*",
          left: { node_type: "variable", value: "n" },
          right: { node_type: "variable", value: "R" },
        },
        right: { node_type: "variable", value: "T" },
      },
      right: { node_type: "variable", value: "V" },
    },
  },
  {
    id: "harmonic-oscillator",
    name: "Harmonic Oscillator Energy",
    tagline: "Potential energy stored in a Hookean spring",
    category: "Oscillations",
    formulaLatex: "(0.5 \\cdot k) \\cdot x^{2}",
    variables: [
      { symbol: "k", name: "Spring Constant", unit: "newton / meter", domain: "positive_real", latex_presentation: "k" },
      { symbol: "x", name: "Displacement", unit: "meter", domain: "real", latex_presentation: "x" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "constant", value: 0.5 },
        right: { node_type: "variable", value: "k" },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "x" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
];

const CATEGORY_ICONS: Record<PresetCategory, React.ComponentType<{ className?: string }>> = {
  Classical: Atom,
  Relativistic: Zap,
  Astrophysics: Orbit,
  Thermodynamics: Flame,
  Oscillations: Activity,
};

const CATEGORY_COLORS: Record<PresetCategory, { badge: string; glow: string; text: string }> = {
  Classical: {
    badge: "bg-blue-500/10 border-blue-500/30 text-blue-400",
    glow: "hover:border-blue-500/50 hover:shadow-blue-500/10",
    text: "text-blue-400",
  },
  Relativistic: {
    badge: "bg-purple-500/10 border-purple-500/30 text-purple-400",
    glow: "hover:border-purple-500/50 hover:shadow-purple-500/10",
    text: "text-purple-400",
  },
  Astrophysics: {
    badge: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    glow: "hover:border-amber-500/50 hover:shadow-amber-500/10",
    text: "text-amber-400",
  },
  Thermodynamics: {
    badge: "bg-rose-500/10 border-rose-500/30 text-rose-400",
    glow: "hover:border-rose-500/50 hover:shadow-rose-500/10",
    text: "text-rose-400",
  },
  Oscillations: {
    badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    glow: "hover:border-emerald-500/50 hover:shadow-emerald-500/10",
    text: "text-emerald-400",
  },
};

interface ScientificPresetsBarProps {
  onSelectPreset: (preset: ScientificPreset) => void;
  className?: string;
}

export const ScientificPresetsBar: React.FC<ScientificPresetsBarProps> = ({
  onSelectPreset,
  className = "",
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  const categories = ["All", "Classical", "Relativistic", "Astrophysics", "Thermodynamics", "Oscillations"];

  const filteredPresets =
    selectedCategory === "All"
      ? CANONICAL_PRESETS
      : CANONICAL_PRESETS.filter((p) => p.category === selectedCategory);

  return (
    <div
      className={`rounded-2xl border border-slate-700/60 bg-slate-900/80 backdrop-blur-xl p-5 shadow-2xl ${className}`}
      data-testid="scientific-presets-bar"
    >
      {/* Header and Filter Pills */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
              1-Click Scientific Presets Engine
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-cyan-400" />
            Pre-Verified Physical Laws & Formulas
          </h2>
          <p className="text-xs text-slate-400">
            Instant 1-click loading with canonical Pint SI units and automatic 6-layer verification run.
          </p>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5" role="tablist">
          {categories.map((cat) => (
            <button
              key={cat}
              role="tab"
              aria-selected={selectedCategory === cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-all border ${
                selectedCategory === cat
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-sm shadow-cyan-500/20"
                  : "bg-slate-800/60 text-slate-400 border-slate-700/60 hover:text-slate-200 hover:border-slate-600"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Preset Cards Grid */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
        {filteredPresets.map((preset) => {
          const CategoryIcon = CATEGORY_ICONS[preset.category];
          const colorConfig = CATEGORY_COLORS[preset.category];

          return (
            <div
              key={preset.id}
              onClick={() => onSelectPreset(preset)}
              className={`group relative flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl cursor-pointer ${colorConfig.glow}`}
            >
              <div>
                {/* Card Header: Category Badge & Variables Count */}
                <div className="flex items-center justify-between mb-2.5">
                  <span
                    className={`inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${colorConfig.badge}`}
                  >
                    <CategoryIcon className="w-3 h-3" />
                    {preset.category}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {preset.variables.length} vars
                  </span>
                </div>

                {/* Title & Tagline */}
                <h3 className="text-sm font-bold text-slate-100 group-hover:text-cyan-300 transition-colors flex items-center justify-between">
                  <span>{preset.name}</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                  {preset.tagline}
                </p>

                {/* KaTeX Math Formula Preview Chip */}
                <div className="my-3 rounded-lg border border-slate-800/80 bg-slate-900/90 py-2.5 px-3 text-center min-h-[46px] flex items-center justify-center overflow-x-auto shadow-inner">
                  <KatexFormula math={preset.formulaLatex} />
                </div>

                {/* Variable Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {preset.variables.map((v) => (
                    <span
                      key={v.symbol}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/50"
                      title={`${v.name}: ${v.unit}`}
                    >
                      {v.symbol} <span className="text-slate-500">[{v.unit}]</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* 1-Click Load Preset Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectPreset(preset);
                }}
                className="mt-1 w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 transition-all hover:bg-cyan-500/20 hover:border-cyan-400/50 group-hover:shadow-sm group-hover:shadow-cyan-500/20"
              >
                <span>Load Preset</span>
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
