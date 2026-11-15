import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        obsidian: {
          950: "#030712", // Kept for exact test match
          900: "#060911", // Deep cosmic void
          850: "#0a0e1a", // Surface 1: Panel base
          800: "#0f1626", // Surface 2: Elevated slate
          750: "#151d32", // Surface 3: Hover/active slate
          700: "#1e293b",
        },
        science: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9", // electric cyan
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
          950: "#082f49",
        },
        epistemic: {
          cyan: "#0ea5e9",
          emerald: "#10b981",
          violet: "#8b5cf6",
          amber: "#f59e0b",
          ruby: "#ef4444",
        },
      },
      boxShadow: {
        "glow-cyan": "0 0 20px -5px rgba(14, 165, 233, 0.4)",
        "glow-emerald": "0 0 20px -5px rgba(16, 185, 129, 0.4)",
        "glow-violet": "0 0 20px -5px rgba(139, 92, 246, 0.4)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
        // Precision artisanal tactile shadows
        "tactile-card": "0 1px 3px 0 rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.09)",
        "bezel-outer": "0 0 0 1px rgba(255, 255, 255, 0.08), 0 12px 32px -8px rgba(0, 0, 0, 0.7), inset 0 1px 0 0 rgba(255, 255, 255, 0.14)",
        "bezel-hover": "0 0 0 1px rgba(56, 189, 248, 0.35), 0 16px 40px -8px rgba(14, 165, 233, 0.18), inset 0 1px 0 0 rgba(255, 255, 255, 0.22)",
        "node-selected": "0 0 0 1px rgba(56, 189, 248, 0.8), 0 0 20px -2px rgba(14, 165, 233, 0.35), inset 0 1px 0 0 rgba(255, 255, 255, 0.2)",
        "node-dragging": "0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(14, 165, 233, 0.35)",
        "inner-slate": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.6)",
      },
      backgroundImage: {
        "lab-grid": "linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px)",
        "radial-spotlight": "radial-gradient(1000px circle at 50% -20%, rgba(14, 165, 233, 0.12), rgba(15, 23, 42, 0.02) 60%, transparent 100%)",
      },
      animation: {
        "pulse-flow": "pulseFlow 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        pulseFlow: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.6", transform: "scale(0.98)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
