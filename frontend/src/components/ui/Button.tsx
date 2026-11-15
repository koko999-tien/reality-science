import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline";
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  className = "",
  ...props
}) => {
  const base =
    "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-tactile-card";
  const variants = {
    primary:
      "bg-cyan-600 text-white hover:bg-cyan-500 border border-cyan-400/30 hover:border-cyan-400/60 shadow-glow-cyan",
    secondary:
      "bg-slate-900 text-slate-100 hover:bg-slate-800 border border-white/[0.1] hover:border-white/20",
    outline:
      "border border-white/[0.12] bg-transparent text-slate-300 hover:bg-slate-900/60 hover:text-white hover:border-cyan-500/40",
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
};
