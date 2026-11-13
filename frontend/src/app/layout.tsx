import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "REALITY SCIENCE — Evidence-Driven Scientific Verification Platform",
  description: "Mathematically rigorous scientific hypothesis verification and reality constraint engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
