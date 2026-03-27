import type { ReactNode } from "react";

const toneClasses = {
  cyan: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
  green: "border-emerald-300/35 bg-emerald-300/10 text-emerald-100",
  orange: "border-orange-300/35 bg-orange-300/10 text-orange-100",
  red: "border-red-300/35 bg-red-300/10 text-red-100",
  yellow: "border-yellow-300/35 bg-yellow-300/10 text-yellow-100",
  gray: "border-white/15 bg-white/5 text-slate-200",
} as const;

type Tone = keyof typeof toneClasses;

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-[1.75rem] border border-white/15 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] shadow-[0_0_0_1px_rgba(0,212,255,0.05)] ${className}`}
    >
      {children}
    </section>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="space-y-2 border-b border-white/10 px-5 py-4 sm:px-6">
      <p className="font-mono text-[0.7rem] uppercase tracking-[0.32em] text-cyan-200/70">
        {eyebrow}
      </p>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {description ? (
          <p className="max-w-2xl text-sm leading-6 text-slate-400">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function Pill({
  tone = "gray",
  children,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 font-mono text-[0.7rem] uppercase tracking-[0.22em] ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
      <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-sm text-white">{value}</p>
    </div>
  );
}

