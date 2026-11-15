import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Input: React.FC<InputProps> = ({ label, id, className = "", ...props }) => {
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={id} className="block text-xs font-mono font-medium text-slate-300">
          {label}
        </label>
      )}
      <input
        id={id}
        className={`w-full rounded-lg border border-white/[0.1] bg-[#060a10] px-3 py-2 text-sm text-slate-100 placeholder-slate-500 shadow-inner focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors ${className}`}
        {...props}
      />
    </div>
  );
};
