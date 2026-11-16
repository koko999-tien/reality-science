import React from "react";
import Link from "next/link";
import { Atom, Layers, Github, ExternalLink } from "lucide-react";

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-slate-950/80 border-b border-white/10 transition-colors shadow-tactile-card">
      <div className="container mx-auto flex min-h-16 flex-wrap items-center justify-between gap-2 px-4 py-3 sm:h-16 sm:px-6 sm:py-0">
        {/* Brand identity */}
        <Link
          href="/"
          className="group flex items-center gap-3 transition-opacity hover:opacity-95"
          aria-label="REALITY SCIENCE Home"
        >
          <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 shadow-glow-cyan transition-transform group-hover:scale-105">
            <Atom className="h-5 w-5 text-cyan-400" />
            <div className="absolute inset-0 rounded-lg bg-cyan-400/10 blur-sm -z-10" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-extrabold tracking-wider text-white font-sans flex items-center gap-1.5">
              REALITY<span className="text-cyan-400">SCIENCE</span>
            </span>
            <span className="text-[10px] font-mono tracking-widest text-cyan-400/90 uppercase font-semibold">
              SCIENTIFIC WORKSPACE
            </span>
          </div>
        </Link>

        {/* Navigation links & Actions */}
        <nav className="flex items-center gap-2 sm:gap-3 text-sm font-medium" aria-label="Main Navigation">
          <Link
            href="/projects"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800/60 border border-transparent hover:border-cyan-500/30 transition-all text-xs sm:text-sm font-semibold"
          >
            <Atom className="h-3.5 w-3.5 text-emerald-300" />
            <span>Projects</span>
          </Link>

          <a
            href="https://github.com/TienNguyenD/Reality_Science"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-900/60 px-3 py-1.5 text-slate-300 hover:text-white hover:border-cyan-500/40 hover:bg-slate-800/80 transition-all text-xs sm:text-sm shadow-sm"
            aria-label="GitHub Repository (opens in new tab)"
          >
            <Github className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">GitHub</span>
            <ExternalLink className="h-3 w-3 text-slate-400" />
          </a>
        </nav>
      </div>
    </header>
  );
};
