"use client";

import React, { useState } from "react";
import { VariableSpec } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { Plus, Trash2, AlertCircle, Info, Sparkles } from "lucide-react";

interface VariableDeclarationPanelProps {
  variables: VariableSpec[];
  onVariablesChange: (variables: VariableSpec[]) => void;
  usedSymbols?: Set<string>;
  className?: string;
}

const COMMON_UNITS = [
  { label: "Dimensionless", value: "dimensionless" },
  { label: "Meter (m)", value: "meter" },
  { label: "Second (s)", value: "second" },
  { label: "Kilogram (kg)", value: "kilogram" },
  { label: "Meter/sec (m/s)", value: "meter / second" },
  { label: "Acceleration (m/s²)", value: "meter / second ** 2" },
  { label: "Newton (N)", value: "newton" },
  { label: "Joule (J)", value: "joule" },
  { label: "Watt (W)", value: "watt" },
  { label: "Pascal (Pa)", value: "pascal" },
];

const DOMAINS: Array<NonNullable<VariableSpec["domain"]>> = [
  "real",
  "positive_real",
  "integer",
  "complex",
];

const SYMBOL_REGEX = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

export const VariableDeclarationPanel: React.FC<VariableDeclarationPanelProps> = ({
  variables,
  onVariablesChange,
  usedSymbols = new Set(),
  className = "",
}) => {
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("meter");
  const [domain, setDomain] = useState<NonNullable<VariableSpec["domain"]>>("real");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedSymbol = symbol.trim();
    const trimmedName = name.trim();
    const trimmedUnit = unit.trim();

    if (!trimmedSymbol) {
      setError("Variable symbol is required.");
      return;
    }

    if (!SYMBOL_REGEX.test(trimmedSymbol)) {
      setError(
        "Invalid symbol format. Must start with a letter or underscore, followed by alphanumeric characters (e.g. 'v', 'x_1', 'mass')."
      );
      return;
    }

    if (variables.some((v) => v.symbol === trimmedSymbol)) {
      setError(`Variable '${trimmedSymbol}' is already declared.`);
      return;
    }

    if (!trimmedName) {
      setError("Descriptive name is required (e.g., 'Velocity', 'Radius').");
      return;
    }

    if (!trimmedUnit) {
      setError("Physical SI unit is required (e.g. 'meter', 'second', 'dimensionless').");
      return;
    }

    const newVar: VariableSpec = {
      symbol: trimmedSymbol,
      name: trimmedName,
      unit: trimmedUnit,
      domain,
      latex_presentation: trimmedSymbol,
    };

    onVariablesChange([...variables, newVar]);
    setSymbol("");
    setName("");
    setUnit("meter");
    setDomain("real");
  };

  const handleDelete = (symToDelete: string) => {
    if (usedSymbols.has(symToDelete)) {
      if (
        !window.confirm(
          `Variable '${symToDelete}' is currently in use on the canvas. Deleting it may cause AST validation errors. Proceed?`
        )
      ) {
        return;
      }
    }
    onVariablesChange(variables.filter((v) => v.symbol !== symToDelete));
  };

  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-emerald-500" />
            Symbol-First Declaration Panel
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Mandatory ADR-001 constraint: Declare symbols and Pint SI units before equation authoring.
          </p>
        </div>
        <span className="text-xs font-mono bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 px-2.5 py-1 rounded-full font-semibold">
          {variables.length} declared
        </span>
      </div>

      {/* Add Variable Form */}
      <form onSubmit={handleAdd} className="mt-4 space-y-3 bg-slate-50 p-4 rounded-xl dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {/* Symbol */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Symbol <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="e.g. v_0"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-mono focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
                aria-label="Variable symbol"
              />
              {symbol && (
                <div className="absolute right-2 top-1.5 text-xs">
                  <KatexFormula math={symbol} />
                </div>
              )}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Initial Velocity"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
              aria-label="Variable name"
            />
          </div>

          {/* Unit */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Pint SI Unit <span className="text-rose-500">*</span>
            </label>
            <div className="flex gap-1.5">
              <input
                type="text"
                list="common-units"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                placeholder="e.g. meter / second"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-mono focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
                aria-label="Physical SI unit"
              />
              <datalist id="common-units">
                {COMMON_UNITS.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </datalist>
            </div>
          </div>

          {/* Domain */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Domain
            </label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value as NonNullable<VariableSpec["domain"]>)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900"
              aria-label="Mathematical domain"
            >
              {DOMAINS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-1.5 text-xs text-rose-600 bg-rose-50 dark:bg-rose-950/50 p-2 rounded-lg">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <Plus className="h-4 w-4" />
            Declare Symbol
          </button>
        </div>
      </form>

      {/* Variables List / Table */}
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
          <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wider dark:bg-slate-950">
            <tr>
              <th className="px-4 py-2.5 text-left font-semibold">Symbol</th>
              <th className="px-4 py-2.5 text-left font-semibold">LaTeX</th>
              <th className="px-4 py-2.5 text-left font-semibold">Name</th>
              <th className="px-4 py-2.5 text-left font-semibold">SI Unit</th>
              <th className="px-4 py-2.5 text-left font-semibold">Domain</th>
              <th className="px-4 py-2.5 text-center font-semibold">Usage</th>
              <th className="px-4 py-2.5 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
            {variables.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-xs text-slate-400 italic">
                  No variables declared yet. Add your model&apos;s physical variables above.
                </td>
              </tr>
            ) : (
              variables.map((v) => {
                const isUsed = usedSymbols.has(v.symbol);
                return (
                  <tr key={v.symbol} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      {v.symbol}
                    </td>
                    <td className="px-4 py-2">
                      <KatexFormula math={v.symbol} />
                    </td>
                    <td className="px-4 py-2 font-medium text-slate-800 dark:text-slate-200">
                      {v.name}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-slate-600 dark:text-slate-400">
                      <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                        {v.unit}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs">
                      <span className="rounded-md bg-blue-50 px-2 py-0.5 font-medium text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                        {v.domain ?? "real"}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-center text-xs">
                      {isUsed ? (
                        <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          In Use
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">Unused</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => handleDelete(v.symbol)}
                        className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/50"
                        title="Delete variable"
                        aria-label={`Delete variable ${v.symbol}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
