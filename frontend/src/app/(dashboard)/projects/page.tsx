import Link from "next/link";

export default function ProjectsDashboardPage() {
  return (
    <div className="container mx-auto p-8 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold">Research Projects</h1>
          <p className="text-sm text-slate-500">Manage mathematical models and reality validation runs</p>
        </div>
        <button className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500">
          + New Project
        </button>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border p-6 space-y-3 dark:border-slate-800">
          <span className="inline-block rounded bg-sky-100 px-2 py-1 text-xs font-semibold text-sky-800 dark:bg-sky-900 dark:text-sky-200">
            Private Draft
          </span>
          <h3 className="text-xl font-bold">Dark Matter Particle Cross-Section</h3>
          <p className="text-sm text-slate-500">
            Astrophysical null result constraints evaluated against Xenon-1T dataset.
          </p>
          <Link href="/projects/dark-matter-particle/editor" className="text-sm font-semibold text-sky-600 hover:underline">
            Open Editor &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
