import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { BinaryOpNode as BinaryOpNodeType } from "@/types/canvas";
import { OperatorType } from "@/types/contracts";
import { KatexFormula } from "@/components/equations/KatexFormula";

const OPERATORS: { op: OperatorType; label: string; symbol: string; latex: string }[] = [
  { op: "+", label: "Add (+)", symbol: "+", latex: "+" },
  { op: "-", label: "Subtract (-)", symbol: "−", latex: "-" },
  { op: "*", label: "Multiply (×)", symbol: "×", latex: "\\cdot" },
  { op: "/", label: "Divide (/)", symbol: "÷", latex: "/" },
  { op: "**", label: "Power (^)", symbol: "^", latex: "x^y" },
];

export const BinaryOpNode: React.FC<NodeProps<BinaryOpNodeType>> = ({
  id,
  data,
  selected = false,
  dragging = false,
}) => {
  const currentOp = data.op ?? "+";
  const activeOp = OPERATORS.find((item) => item.op === currentOp) || OPERATORS[0];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value as OperatorType);
  };

  return (
    <div
      style={{
        transform: dragging ? "scale(1.035) translateY(-4px)" : undefined,
        boxShadow: dragging
          ? "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(245, 158, 11, 0.35)"
          : undefined,
        transition: dragging ? "none" : "all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
      className={`relative rounded-xl border border-amber-500/40 bg-slate-900/90 backdrop-blur-xl p-3.5 shadow-tactile-card min-w-[160px] ${
        selected ? "ring-2 ring-amber-400 shadow-glow-amber" : "ring-1 ring-amber-500/20"
      } hover:border-amber-400/70 transition-all`}
    >
      {/* Left Input Handle (Top) */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ top: "35%" }}
        className="!bg-amber-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
      <span className="absolute left-4 top-[28%] text-[10px] font-mono font-bold text-amber-400/80">
        L
      </span>

      {/* Right Input Handle (Bottom) */}
      <Handle
        type="target"
        position={Position.Left}
        id="right"
        style={{ top: "65%" }}
        className="!bg-amber-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
      <span className="absolute left-4 top-[58%] text-[10px] font-mono font-bold text-amber-400/80">
        R
      </span>

      <div className="flex items-center justify-between mb-1.5 ml-4">
        <div className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
          Binary Op
        </div>
        <div className="text-[10px] font-mono text-amber-300 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/40 shadow-inner">
          <KatexFormula math={activeOp.latex} />
        </div>
      </div>

      <div className="ml-4">
        <select
          value={currentOp}
          onChange={handleChange}
          className="nodrag w-full rounded-lg border border-slate-700 bg-slate-950/90 px-2.5 py-1 text-sm font-bold text-center text-slate-100 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-colors shadow-inner"
          aria-label={`Binary operator for node ${id}`}
        >
          {OPERATORS.map((item) => (
            <option key={item.op} value={item.op}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-amber-500 !w-3 !h-3 !border-2 !border-slate-950 shadow-sm hover:scale-125 transition-transform duration-150"
      />
    </div>
  );
};
