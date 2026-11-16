"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { fetchProjectBySlug } from "@/lib/api";

export function ResearchProjectLookup() {
  const router = useRouter();
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function openProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const projectSlug = slug.trim();
    if (!projectSlug) return;

    setIsLoading(true);
    setError(null);
    try {
      const project = await fetchProjectBySlug(projectSlug);
      router.push(`/projects/${encodeURIComponent(project.slug)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Project could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section id="project-lookup" aria-labelledby="project-lookup-title" className="border-y border-white/10 py-10 sm:py-12">
      <div className="grid gap-6 md:grid-cols-[1fr_minmax(280px,0.8fr)] md:items-end">
        <div>
          <p className="home-kicker">Research workspace</p>
          <h2 id="project-lookup-title" className="text-xl font-semibold text-white sm:text-2xl">
            Open a project record
          </h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">
            Load the project and version information currently available from the research API.
          </p>
        </div>
        <form onSubmit={openProject} className="flex flex-col gap-2 sm:flex-row">
          <label htmlFor="project-slug" className="sr-only">Project identifier</label>
          <input
            id="project-slug"
            name="slug"
            autoComplete="off"
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            placeholder="Project identifier"
            className="min-h-11 min-w-0 flex-1 border border-slate-600 bg-slate-950 px-3 text-sm text-white placeholder:text-slate-500 focus:border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300/30"
          />
          <button
            type="submit"
            disabled={isLoading || !slug.trim()}
            className="inline-flex min-h-11 items-center justify-center gap-2 bg-emerald-200 px-4 text-sm font-semibold text-slate-950 transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" /> : <ArrowRight aria-hidden="true" className="h-4 w-4" />}
            {isLoading ? "Loading" : "Open project"}
          </button>
        </form>
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}
    </section>
  );
}
