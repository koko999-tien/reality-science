import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { BinaryOpNode as BinaryOpNodeType } from "@/types/canvas";
import { OperatorType } from "@/types/contracts";

const OPERATORS: { op: OperatorType; label: string; symbol: string }[] = [
  { op: "+", label: "Add (+)", symbol: "+" },
  { op: "-", label: "Subtract (-)", symbol: "−" },
  { op: "*", label: "Multiply (×)", symbol: "×" },
  { op: "/", label: "Divide (/)", symbol: "÷" },
  { op: "**", label: "Power (^)", symbol: "^" },
];

export const BinaryOpNode: React.FC<NodeProps<BinaryOpNodeType>> = ({ id, data }) => {
  const currentOp = data.op ?? "+";

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value as OperatorType);
  };

  return (
    <div className="relative rounded-lg border-2 border-amber-400 bg-white p-3 shadow-md min-w-[150px] dark:bg-slate-900 dark:border-amber-600">
      {/* Left Input Handle (Top) */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ top: "35%" }}
        className="!bg-amber-500 !w-3 !h-3"
      />
      <span className="absolute left-4 top-[28%] text-[10px] font-bold text-slate-400">
        L
      </span>

      {/* Right Input Handle (Bottom) */}
      <Handle
        type="target"
        position={Position.Left}
        id="right"
        style={{ top: "65%" }}
        className="!bg-amber-500 !w-3 !h-3"
      />
      <span className="absolute left-4 top-[58%] text-[10px] font-bold text-slate-400">
        R
      </span>

      <div className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-1 ml-4">
        Binary Op
      </div>

      <div className="ml-4">
        <select
          value={currentOp}
          onChange={handleChange}
          className="nodrag w-full rounded border border-slate-300 px-2 py-1 text-sm font-bold text-center focus:border-amber-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800"
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
        className="!bg-amber-500 !w-3 !h-3"
      />
    </div>
  );
};
