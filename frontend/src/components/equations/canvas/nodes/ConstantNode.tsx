import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { ConstantNode as ConstantNodeType } from "@/types/canvas";

export const ConstantNode: React.FC<NodeProps<ConstantNodeType>> = ({ id, data }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    const num = parseFloat(val);
    data.onChange?.(isNaN(num) ? val : num);
  };

  return (
    <div className="rounded-lg border-2 border-blue-400 bg-white p-3 shadow-md min-w-[140px] dark:bg-slate-900 dark:border-blue-600">
      <div className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-1">
        Constant
      </div>
      <input
        type="number"
        step="any"
        value={data.value ?? 0}
        onChange={handleChange}
        className="nodrag w-full rounded border border-slate-300 px-2 py-1 text-sm font-mono focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800"
        placeholder="0.0"
        aria-label={`Constant value for node ${id}`}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-blue-500 !w-3 !h-3"
      />
    </div>
  );
};
