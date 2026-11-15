import React from "react";
import Link from "next/link";
import { Atom, Layers, Github, ExternalLink, Sparkles } from "lucide-react";

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-slate-950/80 border-b border-white/10 transition-colors">
      <div className="container mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand identity */}
        <Link
          href="/"
          className="group flex items-center gap-3 transition-opacity hover:opacity-95"
          aria-label="REALITY SCIENCE Home"
        >
          <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 shadow-glow-cyan transition-transform group-hover:scale-105">
            <Atom className="h-5 w-5 animate-pulse text-cyan-400" />
            <div className="absolute inset-0 rounded-lg bg-cyan-400/10 blur-sm -z-10" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-extrabold tracking-wider text-white font-sans flex items-center gap-1.5">
              REALITY<span className="text-cyan-400">SCIENCE</span>
            </span>
            <span className="text-[10px] font-mono tracking-widest text-cyan-400/90 uppercase font-semibold">
              EPITEMIC ENGINE
            </span>
          </div>
        </Link>

        {/* Live operational status pill */}
        <div className="hidden md:flex items-center">
          <div
            className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3 py-1 shadow-sm"
            role="status"
            aria-live="polite"
          >
            <span className="relative flex h-2 w-2" aria-hidden="true">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-xs font-mono font-medium text-emerald-400 tracking-wide">
              6-Layer RCE Engine Online
            </span>
          </div>
        </div>

        {/* Navigation links & Actions */}
        <nav className="flex items-center gap-2 sm:gap-3 text-sm font-medium" aria-label="Main Navigation">
          <Link
            href="/projects/default-model/editor"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800/60 border border-transparent hover:border-cyan-500/30 transition-all text-xs sm:text-sm font-semibold"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <span>Studio Canvas</span>
          </Link>

          <Link
            href="/projects"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800/60 border border-transparent hover:border-cyan-500/30 transition-all text-xs sm:text-sm font-medium"
          >
            <Layers className="h-3.5 w-3.5 text-slate-400" />
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

