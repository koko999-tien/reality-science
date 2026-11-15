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
          950: "#030712",
          900: "#08090a",
          850: "#0b0f19",
          800: "#0f172a",
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

