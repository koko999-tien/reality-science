import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "REALITY SCIENCE — Scientific Research Workspace",
  description:
    "A research workspace for structured mathematical models, physical dimensions, empirical evidence, and reproducible validation runs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
        <body className="antialiased min-h-screen flex flex-col bg-[#030712] text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-100 relative">
        <Navbar />
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
