import type { IncidentStatus } from "../types";

const statusClasses: Record<IncidentStatus, string> = {
  detected: "border-white/15 bg-white/5 text-slate-200",
  stored: "border-white/15 bg-white/5 text-slate-200",
  diagnosing: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
  fixing: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
  gating: "border-orange-300/35 bg-orange-300/10 text-orange-100",
  awaiting_approval: "border-orange-300/35 bg-orange-300/10 text-orange-100",
  deploying: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
  resolved: "border-emerald-300/35 bg-emerald-300/10 text-emerald-100",
  blocked: "border-red-300/35 bg-red-300/10 text-red-100",
  failed: "border-red-300/35 bg-red-300/10 text-red-100",
};

export function StatusBadge({
  status,
  className = "",
}: {
  status: IncidentStatus;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 font-mono text-[0.68rem] uppercase tracking-[0.2em] ${statusClasses[status]} ${className}`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
