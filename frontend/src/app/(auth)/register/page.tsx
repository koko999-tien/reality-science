import React from "react";
import Link from "next/link";
import { Atom, ShieldCheck, UserPlus, ArrowRight } from "lucide-react";

export default function RegisterPage() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 rounded-2xl border border-white/[0.08] bg-slate-900/90 backdrop-blur-xl p-8 shadow-tactile-card">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 mx-auto shadow-glow-cyan">
            <Atom className="h-5 w-5 animate-pulse text-cyan-400" />
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            Create Research Account
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            Register Academic Identifier in Reality Science Repository
          </p>
        </div>

        {/* Security badge */}
        <div className="flex items-center justify-between p-2.5 rounded-lg border border-white/[0.06] bg-slate-950/60 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
            <ShieldCheck className="h-3.5 w-3.5" />
            Cryptographic Provenance
          </span>
          <span className="text-slate-500">SHA-256 Keyed</span>
        </div>

        <form className="space-y-4">
          <div>
            <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
              Display / Citation Name
            </label>
            <input
              type="text"
              required
              className="w-full rounded-lg border border-white/[0.1] bg-[#060a10] px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 shadow-inner focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors"
              placeholder="Dr. Jane Doe"
            />
          </div>
          <div>
            <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              required
              className="w-full rounded-lg border border-white/[0.1] bg-[#060a10] px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 shadow-inner focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors"
              placeholder="researcher@institute.org"
            />
          </div>
          <div>
            <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <input
              type="password"
              required
              className="w-full rounded-lg border border-white/[0.1] bg-[#060a10] px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 shadow-inner focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors"
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-xl bg-cyan-600 hover:bg-cyan-500 py-3 font-semibold text-sm text-white shadow-tactile-card border border-cyan-400/30 transition-all duration-150 active:scale-[0.98] flex items-center justify-center gap-2"
          >
            <UserPlus className="h-4 w-4" />
            <span>Register Actor</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="text-center pt-2 border-t border-white/[0.06]">
          <Link
            href="/login"
            className="text-xs text-slate-400 hover:text-cyan-400 font-mono transition-colors"
          >
            Already registered? Sign in to RCE Console &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
