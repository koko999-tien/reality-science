import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { UnaryOpNode as UnaryOpNodeType } from "@/types/canvas";

export const UnaryOpNode: React.FC<NodeProps<UnaryOpNodeType>> = ({ id }) => {
  return (
    <div className="relative rounded-lg border-2 border-indigo-400 bg-white p-3 shadow-md min-w-[130px] dark:bg-slate-900 dark:border-indigo-600">
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!bg-indigo-500 !w-3 !h-3"
      />
      <div className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-1 text-center">
        Unary Op
      </div>
      <div className="rounded border border-slate-200 bg-slate-50 py-1 text-center font-mono font-bold text-slate-800 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-100">
        Negate (−)
      </div>
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!bg-indigo-500 !w-3 !h-3"
      />
    </div>
  );
};
