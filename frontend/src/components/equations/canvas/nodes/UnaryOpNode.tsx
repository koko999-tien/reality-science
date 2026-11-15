import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { UnaryOpNode as UnaryOpNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";

export const UnaryOpNode: React.FC<NodeProps<UnaryOpNodeType>> = ({
  id,
  selected = false,
  dragging = false,
}) => {
  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(99, 102, 241, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`relative rounded-xl border border-indigo-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-tactile-card min-w-[140px] ${
        selected ? "ring-2 ring-indigo-400 shadow-glow-violet" : "ring-1 ring-indigo-500/20"
      } hover:border-indigo-400/70 transition-all`}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!bg-indigo-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />

      <div className="flex items-center justify-between mb-1.5">
        <div className="text-xs font-mono font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Unary Op
        </div>
        <div className="text-[10px] font-mono text-indigo-300 bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800/40 shadow-inner">
          <KatexFormula math="-x" />
        </div>
      </div>

      <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/50 py-1 px-2.5 text-center font-mono font-bold text-indigo-200 shadow-inner">
        Negate (−)
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-indigo-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
    </div>
  );
};
