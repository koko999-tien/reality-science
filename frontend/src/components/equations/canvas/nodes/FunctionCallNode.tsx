import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { FunctionCallNode as FunctionCallNodeType } from "@/types/canvas";
import { AllowedFunction } from "@/types/contracts";

const FUNCTIONS: { func: AllowedFunction; label: string }[] = [
  { func: "sqrt", label: "sqrt(x)" },
  { func: "sin", label: "sin(x)" },
  { func: "cos", label: "cos(x)" },
  { func: "exp", label: "exp(x)" },
  { func: "log", label: "log(x)" },
];

export const FunctionCallNode: React.FC<NodeProps<FunctionCallNodeType>> = ({ id, data }) => {
  const currentFunc = data.func ?? "sqrt";

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    data.onChange?.(e.target.value as AllowedFunction);
  };

  return (
    <div className="relative rounded-lg border-2 border-rose-400 bg-white p-3 shadow-md min-w-[150px] dark:bg-slate-900 dark:border-rose-600">
      <Handle
        type="target"
        position={Position.Left}
        id="arg0"
        className="!bg-rose-500 !w-3 !h-3"
      />
      <div className="text-xs font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1">
        Function
      </div>
      <select
        value={currentFunc}
        onChange={handleChange}
        className="nodrag w-full rounded border border-slate-300 px-2 py-1 text-sm font-mono focus:border-rose-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800"
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
        className="!bg-rose-500 !w-3 !h-3"
      />
    </div>
  );
};
