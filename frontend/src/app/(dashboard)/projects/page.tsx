import { ResearchProjectLookup } from "@/components/home/ResearchProjectLookup";

export default function ProjectsDashboardPage() {
  return (
    <div className="container mx-auto min-h-[60vh] max-w-7xl px-4 py-10 sm:px-8">
      <div className="max-w-3xl border-b border-white/10 pb-6">
        <p className="home-kicker">Research records</p>
        <h1 className="text-2xl font-semibold text-white sm:text-3xl">Open a scientific project</h1>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          Projects and validation runs are loaded from the research API. No sample records are shown as published or verified work.
        </p>
      </div>
      <div className="mt-2 max-w-3xl">
        <ResearchProjectLookup />
      </div>
    </div>
  );
}
