import React from "react";
import { Plus, Sparkles, Trash2, CheckCircle2 } from "lucide-react";

export type NodeTypeToAdd =
  | "constant"
  | "variable"
  | "binary_op"
  | "unary_op"
  | "function_call"
  | "equation_root";

interface CanvasToolbarProps {
  onAddNode: (type: NodeTypeToAdd) => void;
  onAutoLayout?: () => void;
  onClear?: () => void;
  onValidate?: () => void;
  isValidating?: boolean;
}

export const CanvasToolbar: React.FC<CanvasToolbarProps> = ({
  onAddNode,
  onAutoLayout,
  onClear,
  onValidate,
  isValidating = false,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white/95 px-4 py-2.5 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
      {/* Node creation palette */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Add Node:
        </span>

        <button
          type="button"
          onClick={() => onAddNode("constant")}
          className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/60 dark:text-blue-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Constant
        </button>

        <button
          type="button"
          onClick={() => onAddNode("variable")}
          className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Variable
        </button>

        <button
          type="button"
          onClick={() => onAddNode("binary_op")}
          className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 transition hover:bg-amber-100 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Binary Op
        </button>

        <button
          type="button"
          onClick={() => onAddNode("unary_op")}
          className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 dark:border-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Unary Op
        </button>

        <button
          type="button"
          onClick={() => onAddNode("function_call")}
          className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 transition hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950/60 dark:text-rose-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Function
        </button>

        <button
          type="button"
          onClick={() => onAddNode("equation_root")}
          className="inline-flex items-center gap-1 rounded-md border border-sky-300 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-800 transition hover:bg-sky-100 dark:border-sky-800 dark:bg-sky-950/80 dark:text-sky-200"
        >
          <Plus className="h-3.5 w-3.5" />
          Equation Root
        </button>
      </div>

      {/* Canvas actions */}
      <div className="flex items-center gap-2">
        {onAutoLayout && (
          <button
            type="button"
            onClick={onAutoLayout}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            title="Auto-organize graph layout"
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            Auto Layout
          </button>
        )}

        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-rose-50 hover:text-rose-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-rose-950/40"
            title="Clear all nodes and edges"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        )}

        {onValidate && (
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating}
            className="inline-flex items-center gap-1.5 rounded-md bg-sky-600 px-3 py-1 text-xs font-semibold text-white shadow transition hover:bg-sky-500 disabled:opacity-50"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            {isValidating ? "Validating..." : "Validate AST"}
          </button>
        )}
      </div>
    </div>
  );
};
