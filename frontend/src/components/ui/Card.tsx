import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = "" }) => {
  return (
    <div
      className={`rounded-2xl border border-white/[0.08] bg-slate-900/80 backdrop-blur-xl p-6 shadow-tactile-card transition-all duration-200 ${className}`}
    >
      {children}
    </div>
  );
};
