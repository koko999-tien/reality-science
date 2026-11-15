import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { EquationRootNode as EquationRootNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { Play } from "lucide-react";
import { formatEvaluatedValue } from "@/lib/formula_evaluator";

export const EquationRootNode: React.FC<NodeProps<EquationRootNodeType>> = ({
  id,
  data,
  selected = false,
  dragging = false,
}) => {
  const computedVal = (data as Record<string, unknown>).computedValue as number | null | undefined;

  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(14, 165, 233, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`relative rounded-2xl border border-sky-500/50 bg-slate-900/95 backdrop-blur-xl p-4 shadow-tactile-card min-w-[240px] max-w-[360px] ${
        selected ? "ring-2 ring-sky-400 shadow-glow-cyan" : "ring-1 ring-sky-500/30"
      } hover:border-sky-400/80 transition-all`}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!bg-sky-500 !w-3.5 !h-3.5 !border-2 !border-slate-950 shadow-sm shadow-sky-500/50 hover:scale-125 transition-transform duration-150"
      />

      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          Equation Root {data.name ? `(${data.name})` : ""}
        </span>
        <span className="text-[10px] bg-sky-950/80 text-sky-300 border border-sky-800/60 px-2 py-0.5 rounded-full font-mono">
          Sink
        </span>
      </div>

      <div className="nodrag my-2.5 rounded-xl border border-slate-800 bg-slate-950/90 p-3 text-center min-h-[52px] flex flex-col items-center justify-center overflow-x-auto shadow-inner">
        {data.latex ? (
          <KatexFormula math={data.latex} />
        ) : (
          <span className="text-xs italic text-slate-500">Connect expression to preview</span>
        )}

        {computedVal !== undefined && (
          <div className="mt-1 pt-1 border-t border-white/[0.06] text-[11px] font-mono text-cyan-300 flex items-center gap-1">
            <span className="text-slate-400">Result:</span>
            <span className="font-bold">{formatEvaluatedValue(computedVal)}</span>
          </div>
        )}
      </div>

      {data.onValidate && (
        <button
          type="button"
          onClick={() => data.onValidate?.()}
          className="nodrag mt-2 w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 px-3.5 py-2 text-xs font-semibold text-white shadow-tactile-card border border-cyan-400/40 transition-all focus:outline-none focus:ring-2 focus:ring-cyan-400 cursor-pointer active:scale-[0.98]"
          aria-label="Validate equation"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          Validate equation
        </button>
      )}
    </div>
  );
};
