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

export const FunctionCallNode: React.FC<NodeProps<FunctionCallNodeType>> = ({
  id,
  data,
  selected = false,
  dragging = false,
}) => {
  const currentFunc = data.func ?? "sqrt";
  const activeFunc = FUNCTIONS.find((f) => f.func === currentFunc) || FUNCTIONS[0];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value as AllowedFunction);
  };

  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(244, 63, 94, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`relative rounded-xl border border-rose-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-tactile-card min-w-[160px] ${
        selected ? "ring-2 ring-rose-400 shadow-glow-rose" : "ring-1 ring-rose-500/20"
      } hover:border-rose-400/70 transition-all`}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="arg0"
        className="!bg-rose-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />

      <div className="flex items-center justify-between mb-1.5">
        <div className="text-xs font-mono font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
          Function
        </div>
        <div className="text-[10px] font-mono text-rose-300 bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-800/40 shadow-inner">
          <KatexFormula math={activeFunc.latex} />
        </div>
      </div>

      <select
        value={currentFunc}
        onChange={handleChange}
        className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/90 px-2.5 py-1 text-sm font-mono text-slate-100 focus:border-rose-500 focus:outline-none focus:ring-1 focus:ring-rose-500 transition-colors shadow-inner"
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
        className="!bg-rose-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
    </div>
  );
};
