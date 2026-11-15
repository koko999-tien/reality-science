import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { ConstantNode as ConstantNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";

export const ConstantNode: React.FC<NodeProps<ConstantNodeType>> = ({
  id,
  data,
  selected = false,
  dragging = false,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    const num = parseFloat(val);
    data.onChange?.(isNaN(num) ? val : num);
  };

  const displayVal = data.value ?? 0;

  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(59, 130, 246, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`group relative rounded-xl border border-blue-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-tactile-card min-w-[150px] ${
        selected ? "ring-2 ring-blue-400 shadow-glow-cyan" : "ring-1 ring-blue-500/20"
      } hover:border-blue-400/70 transition-all`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
          Constant
        </div>
        <div className="text-[10px] font-mono text-blue-300 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-800/50 shadow-inner">
          <KatexFormula math={String(displayVal)} />
        </div>
      </div>

      <input
        type="number"
        step="any"
        value={data.value ?? 0}
        onChange={handleChange}
        className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/90 px-2.5 py-1 text-sm font-mono text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors shadow-inner"
        placeholder="0.0"
        aria-label={`Constant value for node ${id}`}
      />

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-blue-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
    </div>
  );
};
