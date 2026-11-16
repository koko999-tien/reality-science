"use client";

import Link from "next/link";
import { ArrowRight, Github, ExternalLink } from "lucide-react";
import { ResearchProjectLookup } from "@/components/home/ResearchProjectLookup";
import { ScientificModelExample } from "@/components/home/ScientificModelExample";
import { FeaturePillars } from "@/components/home/FeaturePillars";

export default function HomePage() {
  return (
    <div className="reality-home min-h-screen bg-[#07100f] text-[#ecf2ed] antialiased">
      <nav className="home-nav mx-auto max-w-7xl px-4 py-4 sm:px-8" role="navigation" aria-label="Main navigation">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg font-mono font-semibold text-white">REALITY SCIENCE</span>
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase text-emerald-300 border border-emerald-500/30 rounded">
              Research workspace
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link className="home-nav-link" href="/projects">
              Projects
            </Link>
            <Link className="home-nav-link" href="#project-lookup">
              Open project
            </Link>
          </div>
        </div>
      </nav>

      <section className="home-hero mx-auto max-w-7xl px-4 pb-16 pt-8 sm:px-8 sm:pt-16" aria-labelledby="home-title">
        <div className="home-hero-grid">
          <div className="home-intro">
            <p className="home-kicker">A workspace for scientific models</p>
            <h1 id="home-title" className="home-title">REALITY SCIENCE</h1>
            <p className="home-lede">
              Build an equation, inspect its physical dimensions, and keep the evidence that supports a result in view.
            </p>
            <div className="home-actions">
              <Link className="home-primary" href="/projects">
                Explore research projects
                <ArrowRight aria-hidden="true" size={17} />
              </Link>
              <Link className="home-secondary" href="#project-lookup">
                Open a project record
              </Link>
            </div>
            <p className="home-note">No synthetic results. No fabricated verification. Only what the backend returns.</p>
          </div>

          <div className="home-model" aria-label="Illustrative equation with dimensional analysis and evidence status">
            <div className="model-header">
              <span className="model-badge">MODEL VIEW</span>
              <span className="model-context">Illustrative example</span>
            </div>
            <div className="model-grid">
              <div className="equation-panel">
                <p className="model-label">Equation</p>
                <div className="equation">v = v₀ + at</div>
                <div className="term-list" aria-label="Variable dimensions">
                  <span><b>v</b><small>m s⁻¹</small></span>
                  <span><b>v₀</b><small>m s⁻¹</small></span>
                  <span><b>a</b><small>m s⁻²</small></span>
                  <span><b>t</b><small>s</small></span>
                </div>
                <p className="dimension-proof">[L T⁻¹] + [L T⁻²][T] = [L T⁻¹]</p>
              </div>

              <div className="plot-panel">
                <div className="plot-heading">
                  <div>
                    <p className="model-label">Illustrative response</p>
                    <strong>Velocity over time</strong>
                  </div>
                  <span className="plot-unit">m s⁻¹</span>
                </div>
                <svg className="model-plot" viewBox="0 0 460 170" role="img" aria-labelledby="plot-title plot-desc">
                  <title id="plot-title">Illustrative linear velocity curve</title>
                  <desc id="plot-desc">A rising line shows velocity increasing with time under constant acceleration.</desc>
                  <path d="M44 18V139H445" fill="none" stroke="#73827a" strokeWidth="1" />
                  <path d="M44 104H445M44 68H445M44 32H445" fill="none" stroke="#273a34" strokeWidth="1" strokeDasharray="3 5" />
                  <path d="M57 119L423 34" fill="none" stroke="#d7c477" strokeWidth="3" />
                  <circle cx="57" cy="119" r="4" fill="#d7c477" />
                  <circle cx="423" cy="34" r="4" fill="#d7c477" />
                  <text x="43" y="158">0</text><text x="403" y="158">time (s)</text>
                  <text x="12" y="28">v</text>
                </svg>
                <div className="plot-caption"><span>Constant acceleration</span><span>Conceptual, not measured data</span></div>
              </div>
            </div>
            <div className="evidence-strip">
              <span className="evidence-mark" aria-hidden="true">i</span>
              <p><strong>Method:</strong> dimensional consistency check <span className="evidence-sep" aria-hidden="true">·</span> <strong>Evidence:</strong> no experimental dataset attached <span className="evidence-sep" aria-hidden="true">·</span> <strong>Status:</strong> not run</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 sm:px-8" aria-labelledby="model-example-title">
        <ScientificModelExample />
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 sm:px-8" aria-labelledby="project-lookup-title">
        <ResearchProjectLookup />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-8 sm:py-20" aria-labelledby="features-title">
        <FeaturePillars />
      </section>

      <section className="home-close mx-auto max-w-7xl px-4 py-16 sm:px-8 sm:py-20" aria-labelledby="continue-title">
        <div className="home-close-content">
          <p className="home-kicker">Continue your work</p>
          <h2 id="continue-title">Inspect a model in the workspace</h2>
        </div>
        <Link className="home-primary" href="/projects">
          Browse projects
          <ArrowRight aria-hidden="true" size={17} />
        </Link>
      </section>

      <footer className="home-footer px-4 py-10 sm:px-8" role="contentinfo">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <span className="text-lg font-mono font-semibold text-white">REALITY SCIENCE</span>
            <span className="footer-note">Research tooling for inspectable models</span>
          </div>
          <a className="footer-link" href="https://github.com/TienNguyenD/Reality_Science" target="_blank" rel="noopener noreferrer">
            Source repository
            <ExternalLink aria-hidden="true" size={13} />
            <Github aria-hidden="true" size={15} />
          </a>
        </div>
      </footer>
    </div>
  );
}