import React from "react";
import Link from "next/link";
import { Layers, ShieldCheck, Activity, Database, GitBranch } from "lucide-react";

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-white/[0.08] bg-slate-950/80 p-6 backdrop-blur-xl shadow-tactile-card min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400/80 flex items-center gap-1.5 mb-3">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            Verification Navigation
          </div>
          <ul className="space-y-1.5 text-xs font-mono">
            <li>
              <Link
                href="/projects"
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-900 border border-transparent hover:border-white/[0.08] transition-all shadow-sm"
              >
                <Layers className="h-3.5 w-3.5 text-cyan-400" />
                <span>Model Overview</span>
              </Link>
            </li>
            <li>
              <Link
                href="/projects"
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-900 border border-transparent hover:border-white/[0.08] transition-all shadow-sm"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Validation Runs</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="pt-4 border-t border-white/[0.06]">
          <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">
            Axiomatic Layers
          </div>
          <div className="space-y-1 text-[11px] font-mono text-slate-400">
            <div className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/50">
              <span>L1 Syntax &amp; Depth</span>
              <span className="text-emerald-400 text-[10px]">PASS</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/50">
              <span>L2 Asymptotics</span>
              <span className="text-emerald-400 text-[10px]">PASS</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/50">
              <span>L3 Pint Dimensions</span>
              <span className="text-emerald-400 text-[10px]">PASS</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/50">
              <span>L4 Noether Conservation</span>
              <span className="text-emerald-400 text-[10px]">PASS</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
