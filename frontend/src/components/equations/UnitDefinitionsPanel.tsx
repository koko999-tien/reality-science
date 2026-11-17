"use client";
import { useState } from "react";
import type { UnitSpec } from "@/types/contracts";

export function UnitDefinitionsPanel({ units, onChange }: { units: UnitSpec[]; onChange: (units: UnitSpec[]) => void }) {
  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [dimension, setDimension] = useState("");
  const [scale, setScale] = useState("1");
  const [error, setError] = useState("");
  const inputClass = "w-full min-h-10 border border-slate-600 bg-slate-950 px-3 text-sm text-slate-100";
  return <details className="border border-slate-700 bg-slate-900/70 p-4">
    <summary className="cursor-pointer text-sm font-semibold">Custom unit definitions ({units.length})</summary>
    <p className="my-3 text-xs text-slate-400">Standard SI units work without a custom definition. Custom definitions are saved with this version.</p>
    <ul className="space-y-2 text-sm">
      {units.map((unit) => <li key={unit.name} className="flex flex-wrap items-center justify-between gap-2">
        <span>{unit.name} ({unit.symbol}) · {unit.dimensionality} · scale {unit.scale_factor ?? 1}</span>
        <button type="button" aria-label={`Remove unit ${unit.name}`} onClick={() => onChange(units.filter((u) => u.name !== unit.name))} className="min-h-10 px-3 text-rose-300">Remove</button>
      </li>)}
    </ul>
    <div className="mt-3 grid gap-3 sm:grid-cols-4">
      <label className="text-xs">Unit name<input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label className="text-xs">Unit symbol<input className={inputClass} value={symbol} onChange={(e) => setSymbol(e.target.value)} /></label>
      <label className="text-xs">Dimensionality<input className={inputClass} placeholder="[length]" value={dimension} onChange={(e) => setDimension(e.target.value)} /></label>
      <label className="text-xs">Scale factor<input className={inputClass} type="number" step="any" value={scale} onChange={(e) => setScale(e.target.value)} /></label>
    </div>
    {error && <p role="alert" className="mt-2 text-sm text-rose-300">{error}</p>}
    <button type="button" className="mt-3 min-h-10 border border-slate-600 px-3 text-sm" onClick={() => {
      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name) || !symbol.trim() || !dimension.trim() || !Number.isFinite(Number(scale)) || Number(scale) <= 0 || units.some((u) => u.name === name)) {
        setError("Use a unique identifier, a symbol, a dimensionality and a positive finite scale."); return;
      }
      onChange([...units, { name, symbol, dimensionality: dimension, scale_factor: Number(scale) }]);
      setName(""); setSymbol(""); setDimension(""); setScale("1"); setError("");
    }}>Add unit definition</button>
  </details>;
}
