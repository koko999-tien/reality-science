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
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/[0.08] bg-slate-900/90 px-4 py-2.5 shadow-tactile-card backdrop-blur-xl">
      {/* Node creation palette */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
          Add Node:
        </span>

        <button
          type="button"
          onClick={() => onAddNode("constant")}
          className="inline-flex items-center gap-1 rounded-lg border border-blue-500/30 bg-blue-950/60 px-2.5 py-1 text-xs font-medium text-blue-300 transition-all hover:bg-blue-900/60 hover:border-blue-400/50 active:scale-[0.98]"
        >
          <Plus className="h-3.5 w-3.5" />
          Constant
        </button>

        <button
          type="button"
          onClick={() => onAddNode("variable")}
          className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-950/60 px-2.5 py-1 text-xs font-medium text-emerald-300 transition-all hover:bg-emerald-900/60 hover:border-emerald-400/50 active:scale-[0.98]"
        >
          <Plus className="h-3.5 w-3.5" />
          Variable
        </button>

        <button
          type="button"
          onClick={() => onAddNode("binary_op")}
          className="inline-flex items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-950/60 px-2.5 py-1 text-xs font-medium text-amber-300 transition-all hover:bg-amber-900/60 hover:border-amber-400/50 active:scale-[0.98]"
        >
          <Plus className="h-3.5 w-3.5" />
          Binary Op
        </button>

        <button
          type="button"
          onClick={() => onAddNode("unary_op")}
          className="inline-flex items-center gap-1 rounded-lg border border-indigo-500/30 bg-indigo-950/60 px-2.5 py-1 text-xs font-medium text-indigo-300 transition-all hover:bg-indigo-900/60 hover:border-indigo-400/50 active:scale-[0.98]"
        >
          <Plus className="h-3.5 w-3.5" />
          Unary Op
        </button>

        <button
          type="button"
          onClick={() => onAddNode("function_call")}
          className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-950/60 px-2.5 py-1 text-xs font-medium text-rose-300 transition-all hover:bg-rose-900/60 hover:border-rose-400/50 active:scale-[0.98]"
        >
          <Plus className="h-3.5 w-3.5" />
          Function
        </button>

        <button
          type="button"
          onClick={() => onAddNode("equation_root")}
          className="inline-flex items-center gap-1 rounded-lg border border-sky-400/40 bg-sky-950/80 px-2.5 py-1 text-xs font-semibold text-sky-200 transition-all hover:bg-sky-900/80 hover:border-sky-400/70 shadow-glow-cyan active:scale-[0.98]"
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
            className="inline-flex items-center gap-1 rounded-lg border border-white/[0.1] bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-200 transition-all hover:bg-slate-700 hover:border-white/20 active:scale-[0.98]"
            title="Auto-organize graph layout"
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            Auto Layout
          </button>
        )}

        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="inline-flex items-center gap-1 rounded-lg border border-white/[0.1] bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 transition-all hover:bg-rose-950/50 hover:text-rose-300 hover:border-rose-500/40 active:scale-[0.98]"
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
            className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 border border-cyan-400/40 px-3.5 py-1 text-xs font-semibold text-white shadow-tactile-card transition-all disabled:opacity-50 active:scale-[0.98]"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            {isValidating ? "Validating..." : "Validate AST"}
          </button>
        )}
      </div>
    </div>
  );
};
