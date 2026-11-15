import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { EquationRootNode as EquationRootNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";
import { Play } from "lucide-react";

export const EquationRootNode: React.FC<NodeProps<EquationRootNodeType>> = ({ id, data }) => {
  return (
    <div className="relative rounded-2xl border border-sky-500/50 bg-slate-900/95 backdrop-blur-xl p-4 shadow-2xl ring-1 ring-sky-500/30 hover:border-sky-400/80 min-w-[240px] max-w-[360px] transition-all">
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!bg-sky-500 !w-3.5 !h-3.5 !border-2 !border-slate-950 shadow-sm shadow-sky-500/50"
      />

      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          Equation Root {data.name ? `(${data.name})` : ""}
        </span>
        <span className="text-[10px] bg-sky-950/80 text-sky-300 border border-sky-800/60 px-2 py-0.5 rounded-full font-mono">
          Sink
        </span>
      </div>

      <div className="nodrag my-2.5 rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-center min-h-[52px] flex items-center justify-center overflow-x-auto shadow-inner">
        {data.latex ? (
          <KatexFormula math={data.latex} />
        ) : (
          <span className="text-xs italic text-slate-500">Connect expression to preview</span>
        )}
      </div>

      {data.onValidate && (
        <button
          type="button"
          onClick={() => data.onValidate?.()}
          className="nodrag mt-2 w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-sky-500/20 transition-all hover:from-sky-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-sky-400 cursor-pointer"
          aria-label="Validate equation"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          Validate Formula
        </button>
      )}
    </div>
  );
};
