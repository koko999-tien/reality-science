"use client";

import { type KeyboardEvent, useState } from "react";

const EXAMPLES = [
  {
    id: "kinematics",
    label: "Kinematics",
    equation: "v = v₀ + at",
    variables: [
      ["v", "Final velocity", "m s⁻¹"],
      ["v₀", "Initial velocity", "m s⁻¹"],
      ["a", "Acceleration", "m s⁻²"],
      ["t", "Elapsed time", "s"],
    ],
    dimensions: "[L T⁻¹] + [L T⁻²][T] = [L T⁻¹]",
  },
  {
    id: "force",
    label: "Newton's second law",
    equation: "F = ma",
    variables: [
      ["F", "Force", "kg m s⁻²"],
      ["m", "Mass", "kg"],
      ["a", "Acceleration", "m s⁻²"],
    ],
    dimensions: "[M L T⁻²] = [M][L T⁻²]",
  },
  {
    id: "negative-control",
    label: "Incompatible sum",
    equation: "x + t",
    variables: [
      ["x", "Position", "m"],
      ["t", "Time", "s"],
    ],
    dimensions: "[L] + [T] is dimensionally incompatible",
  },
] as const;

function handleExampleTabKeyDown(
  event: KeyboardEvent<HTMLButtonElement>,
  currentIndex: number,
  selectIndex: (index: number) => void
) {
  let nextIndex: number | null = null;

  switch (event.key) {
    case "ArrowRight":
      nextIndex = (currentIndex + 1) % EXAMPLES.length;
      break;
    case "ArrowLeft":
      nextIndex = (currentIndex - 1 + EXAMPLES.length) % EXAMPLES.length;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = EXAMPLES.length - 1;
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

export function ScientificModelExample() {
  const [selectedId, setSelectedId] = useState<(typeof EXAMPLES)[number]["id"]>("kinematics");
  const example = EXAMPLES.find(({ id }) => id === selectedId) ?? EXAMPLES[0];

  return (
    <section data-testid="scientific-preset-demo" aria-labelledby="model-example-title" className="py-10 sm:py-14">
      <div className="mb-6 flex flex-col justify-between gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-end">
        <div>
          <p className="home-kicker">Model structure</p>
          <h2 id="model-example-title" className="text-xl font-semibold text-white sm:text-2xl">Inspect an equation and its units</h2>
        </div>
        <span className="w-fit border border-amber-300/40 px-2.5 py-1 text-xs font-medium text-amber-100">Illustrative examples · no validation run</span>
      </div>

      <div role="tablist" aria-label="Equation examples" className="flex flex-wrap gap-x-5 gap-y-2 border-b border-white/10">
        {EXAMPLES.map((item) => (
          <button
            key={item.id}
            id={`example-tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={selectedId === item.id}
            aria-controls="model-example-panel"
            tabIndex={selectedId === item.id ? 0 : -1}
            onClick={() => setSelectedId(item.id)}
            onKeyDown={(event) => handleExampleTabKeyDown(
              event,
              EXAMPLES.findIndex((exampleItem) => exampleItem.id === item.id),
              (index) => setSelectedId(EXAMPLES[index].id)
            )}
            className={`min-h-10 border-b-2 px-1 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300 ${selectedId === item.id ? "border-emerald-200 text-white" : "border-transparent text-slate-400 hover:text-white"}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div id="model-example-panel" role="tabpanel" aria-labelledby={`example-tab-${example.id}`} tabIndex={0} className="grid gap-8 py-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-300 md:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="text-xs font-medium uppercase text-slate-400">Equation</p>
          <p className="mt-2 break-words font-mono text-3xl text-white">{example.equation}</p>
          <p className="mt-7 text-xs font-medium uppercase text-slate-400">Dimensional relation</p>
          <p className="mt-2 break-words font-mono text-sm leading-6 text-emerald-100">{example.dimensions}</p>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase text-slate-400">Declared quantities</p>
          <div className="divide-y divide-white/10 border-y border-white/10">
            {example.variables.map(([symbol, name, unit]) => (
              <div key={symbol} className="grid grid-cols-[3rem_1fr_auto] gap-3 py-2.5 text-sm">
                <span className="font-mono text-white">{symbol}</span>
                <span className="text-slate-300">{name}</span>
                <span className="font-mono text-slate-400">{unit}</span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-400">
            This is a worked dimensional illustration only. It is not a scientific result, an empirical comparison, or a persisted project record.
          </p>
        </div>
      </div>
    </section>
  );
}
