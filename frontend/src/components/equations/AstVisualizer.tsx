import React from "react";
import { ExprNode } from "@/types/contracts";

interface AstVisualizerProps {
  ast: ExprNode;
}

export const AstVisualizer: React.FC<AstVisualizerProps> = ({ ast }) => {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-xs dark:border-slate-800 dark:bg-slate-950">
      <div className="font-semibold text-slate-500 mb-2">AST Node: {ast.node_type}</div>
      <pre>{JSON.stringify(ast, null, 2)}</pre>
    </div>
  );
};
