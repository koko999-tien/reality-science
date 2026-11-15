import React from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { EquationRootNode as EquationRootNodeType } from "@/types/canvas";
import { KatexFormula } from "@/components/equations/KatexFormula";

export const EquationRootNode: React.FC<NodeProps<EquationRootNodeType>> = ({ id, data }) => {
  return (
    <div className="relative rounded-xl border-2 border-sky-500 bg-white p-4 shadow-lg min-w-[220px] max-w-[340px] dark:bg-slate-900 dark:border-sky-400">
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!bg-sky-500 !w-3.5 !h-3.5"
      />
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
          Equation Root {data.name ? `(${data.name})` : ""}
        </span>
        <span className="text-[10px] bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300 px-1.5 py-0.5 rounded font-mono">
          Sink
        </span>
      </div>

      <div className="nodrag my-2 rounded-md bg-slate-50 p-2.5 text-center dark:bg-slate-800/80 min-h-[48px] flex items-center justify-center overflow-x-auto">
        {data.latex ? (
          <KatexFormula math={data.latex} />
        ) : (
          <span className="text-xs italic text-slate-400">Connect expression to preview</span>
        )}
      </div>

      {data.onValidate && (
        <button
          type="button"
          onClick={() => data.onValidate?.()}
          className="nodrag mt-2 w-full rounded-md bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white shadow transition hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
          aria-label="Validate equation"
        >
          Validate Formula
        </button>
      )}
    </div>
  );
};
