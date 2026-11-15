import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { VariableNode as VariableNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";

export const VariableNode: React.FC<NodeProps<VariableNodeType>> = ({
  id,
  data,
  selected = false,
  dragging = false,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value);
  };

  const available = data.availableSymbols ?? [];
  const selectedSym = data.symbol ?? "";
  const activeVar = available.find((v) => v.symbol === selectedSym);
  const unit = activeVar?.unit ?? data.unit;

  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(16, 185, 129, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`group relative rounded-xl border border-emerald-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-tactile-card min-w-[170px] ${
        selected ? "ring-2 ring-emerald-400 shadow-glow-emerald" : "ring-1 ring-emerald-500/20"
      } hover:border-emerald-400/70 transition-all`}
    >
      <div className="flex items-center justify-between mb-1.5 gap-2">
        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Variable
        </span>
        <div className="flex items-center gap-1">
          {selectedSym && (
            <span className="text-[10px] text-emerald-300 bg-emerald-950/60 px-1 py-0.5 rounded border border-emerald-800/40 shadow-inner">
              <KatexFormula math={selectedSym} />
            </span>
          )}
          {unit && (
            <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/60">
              [{unit}]
            </span>
          )}
        </div>
      </div>

      {available.length > 0 ? (
        <select
          value={selectedSym}
          onChange={handleChange}
          className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/90 px-2.5 py-1 text-sm font-mono text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors shadow-inner"
          aria-label={`Variable symbol for node ${id}`}
        >
          {!selectedSym && <option value="">Select variable...</option>}
          {available.map((v) => (
            <option key={v.symbol} value={v.symbol}>
              {v.symbol} {v.name ? `(${v.name})` : ""}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="text"
          value={selectedSym}
          onChange={(e) => data.onChange?.(e.target.value)}
          className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/90 px-2.5 py-1 text-sm font-mono text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors shadow-inner"
          placeholder="Symbol..."
          aria-label={`Variable symbol for node ${id}`}
        />
      )}

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
    </div>
  );
};
