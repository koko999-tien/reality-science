import React from "react";
import { ExprNode } from "@/types/contracts";
import { Layers, Hash, Variable, Cpu } from "lucide-react";

interface AstVisualizerProps {
  ast: ExprNode;
}

const renderNodeBadge = (node: ExprNode): React.ReactNode => {
  switch (node.node_type) {
    case "constant":
      return (
        <span className="inline-flex items-center gap-1 rounded bg-blue-950/70 border border-blue-800/60 px-2 py-0.5 text-[11px] font-mono text-blue-300">
          <Hash className="w-3 h-3 text-blue-400" />
          const: {String(node.value)}
        </span>
      );
    case "variable":
      return (
        <span className="inline-flex items-center gap-1 rounded bg-emerald-950/70 border border-emerald-800/60 px-2 py-0.5 text-[11px] font-mono text-emerald-300">
          <Variable className="w-3 h-3 text-emerald-400" />
          var: {String(node.value)}
        </span>
      );
    case "binary_op":
      return (
        <span className="inline-flex items-center gap-1 rounded bg-amber-950/70 border border-amber-800/60 px-2 py-0.5 text-[11px] font-mono text-amber-300">
          <Cpu className="w-3 h-3 text-amber-400" />
          op: {node.op}
        </span>
      );
    case "unary_op":
      return (
        <span className="inline-flex items-center gap-1 rounded bg-indigo-950/70 border border-indigo-800/60 px-2 py-0.5 text-[11px] font-mono text-indigo-300">
          negate (−)
        </span>
      );
    case "function_call":
      return (
        <span className="inline-flex items-center gap-1 rounded bg-rose-950/70 border border-rose-800/60 px-2 py-0.5 text-[11px] font-mono text-rose-300">
          func: {node.func}()
        </span>
      );
    default:
      return null;
  }
};

export const AstVisualizer: React.FC<AstVisualizerProps> = ({ ast }) => {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-slate-900/80 p-4 font-mono text-xs shadow-tactile-card backdrop-blur-xl">
      {/* Test-asserted header */}
      <div className="font-semibold text-slate-500 mb-2">AST Node: {ast.node_type}</div>

      {/* Interactive Visual Tree Overview */}
      <div className="mb-3 p-2.5 rounded-lg bg-slate-950/80 border border-white/[0.06] flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase font-bold text-slate-500 flex items-center gap-1">
          <Layers className="w-3 h-3 text-cyan-400" />
          Tree Root:
        </span>
        {renderNodeBadge(ast)}
      </div>

      {/* Raw Canonical JSON Representation (Test invariant) */}
      <pre className="max-h-60 overflow-y-auto rounded-lg bg-slate-950 p-3 text-emerald-400 border border-slate-800/80 shadow-inner">
        {JSON.stringify(ast, null, 2)}
      </pre>
    </div>
  );
};
