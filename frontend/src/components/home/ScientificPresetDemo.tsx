"use client";

import React, { useState } from "react";
import { KatexFormula } from "@/components/equations/KatexFormula";

const examples = [
  {
    id: "velocity",
    title: "Velocity",
    formula: "v = v_0 + a \\cdot t",
    relation: "[L][T]^{-1} = [L][T]^{-1} + [L][T]^{-2} \\cdot [T]",
    variables: "v: m/s · v₀: m/s · a: m/s² · t: s",
  },
  {
    id: "energy",
    title: "Rest energy",
    formula: "E = m \\cdot c^{2}",
    relation: "[M][L]^2[T]^{-2} = [M] \\cdot ([L][T]^{-1})^2",
    variables: "E: J · m: kg · c: m/s",
  },
  {
    id: "gravity",
    title: "Gravitational force",
    formula: "F = G \\cdot \\frac{m_1 \\cdot m_2}{r^{2}}",
    relation: "[M][L][T]^{-2} = [L]^3[M]^{-1}[T]^{-2} \\cdot [M]^2/[L]^2",
    variables: "F: N · G: m³/(kg·s²) · m₁,m₂: kg · r: m",
  },
];

function handleTabKeyDown(
  event: React.KeyboardEvent<HTMLButtonElement>,
  currentIndex: number,
  tabCount: number,
  selectIndex: (index: number) => void
) {
  let nextIndex: number | null = null;

  switch (event.key) {
    case "ArrowRight":
      nextIndex = (currentIndex + 1) % tabCount;
      break;
    case "ArrowLeft":
      nextIndex = (currentIndex - 1 + tabCount) % tabCount;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = tabCount - 1;
      break;
    default:
      return;
  }

  event.preventDefault();
  selectIndex(nextIndex);
  event.currentTarget.parentElement
    ?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
    .item(nextIndex)
    .focus();
}

export const ScientificPresetDemo: React.FC = () => {
  const [selected, setSelected] = useState(examples[0]);
  const [activeTab, setActiveTab] = useState<"dimensions" | "variables">("dimensions");
  const panelId = "illustration-panel";

  return (
    <section
      data-testid="scientific-preset-demo"
      className="border-y border-slate-200 bg-white py-10 text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
      aria-labelledby="illustration-title"
    >
      <header className="mx-auto max-w-6xl px-5">
        <p className="font-mono text-xs uppercase text-slate-500">Illustrative example · not run</p>
        <h2 id="illustration-title" className="mt-2 text-xl font-semibold">Inspect a model&apos;s structure</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-400">
          These equations and unit relationships are examples only. No validation or empirical analysis has been performed.
        </p>
        <div role="tablist" aria-label="Illustrative equation" className="mt-5 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example.id}
              id={`tab-${example.id}`}
              type="button"
              role="tab"
              aria-selected={selected.id === example.id}
              aria-controls={panelId}
              tabIndex={selected.id === example.id ? 0 : -1}
              onClick={() => setSelected(example)}
              onKeyDown={(event) => handleTabKeyDown(
                event,
                examples.findIndex((item) => item.id === example.id),
                examples.length,
                (index) => setSelected(examples[index])
              )}
              className="rounded border border-slate-300 px-3 py-2 text-sm hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-slate-700 dark:hover:bg-slate-900"
            >
              {example.title}
            </button>
          ))}
        </div>
      </header>

      <div
        id={panelId}
        role="tabpanel"
        aria-labelledby={`tab-${selected.id}`}
        tabIndex={0}
        className="mx-auto mt-6 max-w-6xl px-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
      >
        <div className="grid gap-6 md:grid-cols-2">
          <div className="min-w-0 border-l-2 border-blue-600 pl-4">
            <p className="font-mono text-xs text-slate-500">Equation · {selected.title}</p>
            <div className="mt-4 overflow-x-auto py-3 text-xl"><KatexFormula math={selected.formula} block /></div>
            <p className="mt-3 break-words font-mono text-xs text-slate-600 dark:text-slate-400">
              <span className="sr-only">Illustrative dimensional relationship: </span>
              <KatexFormula math={selected.relation} />
            </p>
          </div>
          <div>
            <div role="tablist" aria-label="Model details" className="flex gap-4 border-b border-slate-200 dark:border-slate-800">
              {(["dimensions", "variables"] as const).map((tab) => (
                <button
                  key={tab}
                  id={`detail-tab-${tab}`}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab}
                  aria-controls="detail-panel"
                  tabIndex={activeTab === tab ? 0 : -1}
                  onClick={() => setActiveTab(tab)}
                  onKeyDown={(event) => handleTabKeyDown(
                    event,
                    tab === "dimensions" ? 0 : 1,
                    2,
                    (index) => setActiveTab(index === 0 ? "dimensions" : "variables")
                  )}
                  className="border-b-2 border-transparent py-2 text-sm capitalize hover:border-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 aria-selected:border-blue-600"
                >
                  {tab}
                </button>
              ))}
            </div>
            <div id="detail-panel" role="tabpanel" aria-labelledby={`detail-tab-${activeTab}`} tabIndex={0} className="py-4 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">
              {activeTab === "dimensions" ? (
                <p>Shown as a symbolic unit relationship for discussion; it is not a validation result.</p>
              ) : (
                <p className="font-mono">{selected.variables}</p>
              )}
            </div>
            <p className="border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-800">
              No dataset, source record, method run, or measured value is attached to this illustration.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
