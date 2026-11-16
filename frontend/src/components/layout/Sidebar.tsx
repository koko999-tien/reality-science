import React from "react";
import Link from "next/link";
import { Layers, ShieldCheck } from "lucide-react";

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-white/[0.08] bg-slate-950/80 p-6 backdrop-blur-xl shadow-tactile-card min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400/80 flex items-center gap-1.5 mb-3">
            Research workspace
          </div>
          <ul className="space-y-1.5 text-xs font-mono">
            <li>
              <Link
                href="/projects"
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-900 border border-transparent hover:border-white/[0.08] transition-all shadow-sm"
              >
                <Layers className="h-3.5 w-3.5 text-cyan-400" />
                <span>Projects</span>
              </Link>
            </li>
            <li>
              <Link
                href="/projects"
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-900 border border-transparent hover:border-white/[0.08] transition-all shadow-sm"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Validation history</span>
              </Link>
            </li>
          </ul>
        </div>

      </div>
    </aside>
  );
};
