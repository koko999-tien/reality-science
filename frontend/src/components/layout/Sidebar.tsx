import React from "react";

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-950">
      <div className="space-y-4">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Navigation</div>
        <ul className="space-y-2 text-sm font-medium">
          <li>
            <a href="/projects" className="block rounded-md px-3 py-2 text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800">
              Overview
            </a>
          </li>
          <li>
            <a href="/projects" className="block rounded-md px-3 py-2 text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800">
              Validation Runs
            </a>
          </li>
        </ul>
      </div>
    </aside>
  );
};
