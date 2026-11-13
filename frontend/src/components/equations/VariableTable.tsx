import React from "react";
import { VariableSpec } from "@/types/contracts";

interface VariableTableProps {
  variables: VariableSpec[];
}

export const VariableTable: React.FC<VariableTableProps> = ({ variables }) => {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th className="px-4 py-2 text-left font-medium">Symbol</th>
            <th className="px-4 py-2 text-left font-medium">Name</th>
            <th className="px-4 py-2 text-left font-medium">Physical Unit</th>
            <th className="px-4 py-2 text-left font-medium">Domain</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {variables.map((v) => (
            <tr key={v.symbol}>
              <td className="px-4 py-2 font-mono font-bold text-sky-600">{v.symbol}</td>
              <td className="px-4 py-2">{v.name}</td>
              <td className="px-4 py-2 font-mono text-slate-500">{v.unit}</td>
              <td className="px-4 py-2">{v.domain ?? "real"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
