import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { UnaryOpNode as UnaryOpNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";

export const UnaryOpNode: React.FC<NodeProps<UnaryOpNodeType>> = ({ id }) => {
  return (
    <div className="relative rounded-xl border border-indigo-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-xl ring-1 ring-indigo-500/20 hover:border-indigo-400/70 hover:shadow-indigo-500/10 min-w-[140px] transition-all">
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!bg-indigo-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm"
      />

      <div className="flex items-center justify-between mb-1.5">
        <div className="text-xs font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Unary Op
        </div>
        <div className="text-[10px] font-mono text-indigo-300 bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800/40">
          <KatexFormula math="-x" />
        </div>
      </div>

      <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/40 py-1 px-2.5 text-center font-mono font-bold text-indigo-200">
        Negate (−)
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-indigo-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm"
      />
    </div>
  );
};
