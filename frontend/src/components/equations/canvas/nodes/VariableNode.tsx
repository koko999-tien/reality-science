import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { VariableNode as VariableNodeType } from "@/types/canvas";

export const VariableNode: React.FC<NodeProps<VariableNodeType>> = ({ id, data }) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value);
  };

  const available = data.availableSymbols ?? [];
  const selectedSym = data.symbol ?? "";
  const activeVar = available.find((v) => v.symbol === selectedSym);
  const unit = activeVar?.unit ?? data.unit;

  return (
    <div className="rounded-lg border-2 border-emerald-400 bg-white p-3 shadow-md min-w-[160px] dark:bg-slate-900 dark:border-emerald-600">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
          Variable
        </span>
        {unit && (
          <span className="text-[10px] font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
            [{unit}]
          </span>
        )}
      </div>

      {available.length > 0 ? (
        <select
          value={selectedSym}
          onChange={handleChange}
          className="nodrag w-full rounded border border-slate-300 px-2 py-1 text-sm font-mono focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800"
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
          className="nodrag w-full rounded border border-slate-300 px-2 py-1 text-sm font-mono focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800"
          placeholder="Symbol..."
          aria-label={`Variable symbol for node ${id}`}
        />
      )}

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-emerald-500 !w-3 !h-3"
      />
    </div>
  );
};
