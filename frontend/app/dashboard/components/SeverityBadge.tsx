import type { IncidentSeverity } from "../types";

const severityClasses: Record<IncidentSeverity, string> = {
  critical: "border-[#ff4444]/45 bg-[#ff4444]/12 text-[#ffd6d6]",
  high: "border-[#ff8800]/45 bg-[#ff8800]/12 text-[#ffe0c2]",
  medium: "border-[#ffcc00]/45 bg-[#ffcc00]/12 text-[#fff0b8]",
  low: "border-[#00ff88]/45 bg-[#00ff88]/12 text-[#c8ffe4]",
  pending: "border-white/15 bg-white/5 text-slate-200",
};

export function SeverityBadge({
  severity,
  className = "",
}: {
  severity: IncidentSeverity;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 font-mono text-[0.68rem] uppercase tracking-[0.22em] ${severityClasses[severity]} ${className}`}
    >
      {severity}
    </span>
  );
}
