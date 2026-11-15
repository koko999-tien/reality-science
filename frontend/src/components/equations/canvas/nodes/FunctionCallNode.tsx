import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { FunctionCallNode as FunctionCallNodeType } from "@/types/canvas";
import { AllowedFunction } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";

const FUNCTIONS: { func: AllowedFunction; label: string; latex: string }[] = [
  { func: "sqrt", label: "sqrt(x)", latex: "\\sqrt{x}" },
  { func: "sin", label: "sin(x)", latex: "\\sin(x)" },
  { func: "cos", label: "cos(x)", latex: "\\cos(x)" },
  { func: "exp", label: "exp(x)", latex: "e^x" },
  { func: "log", label: "log(x)", latex: "\\ln(x)" },
];

export const FunctionCallNode: React.FC<NodeProps<FunctionCallNodeType>> = ({ id, data }) => {
  const currentFunc = data.func ?? "sqrt";
  const activeFunc = FUNCTIONS.find((f) => f.func === currentFunc) || FUNCTIONS[0];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value as AllowedFunction);
  };

  return (
    <div className="relative rounded-xl border border-rose-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-xl ring-1 ring-rose-500/20 hover:border-rose-400/70 hover:shadow-rose-500/10 min-w-[160px] transition-all">
      <Handle
        type="target"
        position={Position.Left}
        id="arg0"
        className="!bg-rose-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm"
      />

      <div className="flex items-center justify-between mb-1.5">
        <div className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
          Function
        </div>
        <div className="text-[10px] font-mono text-rose-300 bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-800/40">
          <KatexFormula math={activeFunc.latex} />
        </div>
      </div>

      <select
        value={currentFunc}
        onChange={handleChange}
        className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/80 px-2.5 py-1 text-sm font-mono text-slate-100 focus:border-rose-500 focus:outline-none focus:ring-1 focus:ring-rose-500 transition-colors"
        aria-label={`Function call for node ${id}`}
      >
        {FUNCTIONS.map((item) => (
          <option key={item.func} value={item.func}>
            {item.label}
          </option>
        ))}
      </select>

      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-rose-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm"
      />
    </div>
  );
};
