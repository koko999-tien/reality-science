import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-3xl space-y-6">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl text-sky-900 dark:text-sky-100">
          REALITY SCIENCE
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-300">
          Evidence-Driven Scientific Hypothesis &amp; Mathematical Verification Engine.
        </p>
        <div className="flex justify-center gap-4 pt-4">
          <Link
            href="/projects"
            className="rounded-lg bg-sky-600 px-6 py-3 font-semibold text-white shadow-md hover:bg-sky-500 transition"
          >
            Explore Projects
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-slate-300 px-6 py-3 font-semibold hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition"
          >
            Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
