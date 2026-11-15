import React from "react";
import Link from "next/link";

export const Navbar: React.FC = () => {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-xl font-bold tracking-tight text-sky-600">
          REALITY SCIENCE
        </Link>
        <nav className="flex items-center space-x-4 text-sm font-medium">
          <Link href="/projects" className="text-slate-600 hover:text-sky-600 dark:text-slate-300">
            Projects
          </Link>
          <Link href="/login" className="text-slate-600 hover:text-sky-600 dark:text-slate-300">
            Sign In
          </Link>
        </nav>
      </div>
    </header>
  );
};
