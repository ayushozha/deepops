import type { Incident } from "../types";
import { Panel, SectionHeader } from "./dashboard-ui";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";

function shortId(id: string) {
  return id.length > 10 ? `${id.slice(0, 4)}…${id.slice(-4)}` : id;
}

function formatRelativeTime(timestampMs: number) {
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const diffMs = timestampMs - Date.now();
  const diffMinutes = Math.round(diffMs / 60_000);

  if (Math.abs(diffMinutes) < 60) {
    return formatter.format(diffMinutes, "minute");
  }

  const diffHours = Math.round(diffMs / 3_600_000);
  if (Math.abs(diffHours) < 24) {
    return formatter.format(diffHours, "hour");
  }

  const diffDays = Math.round(diffMs / 86_400_000);
  return formatter.format(diffDays, "day");
}

export function IncidentList({
  incidents,
  selectedIncidentId,
  onSelect,
}: {
  incidents: Incident[];
  selectedIncidentId: string | null;
  onSelect: (incidentId: string) => void;
}) {
  return (
    <Panel className="flex h-full min-h-[34rem] flex-col overflow-hidden">
      <SectionHeader
        eyebrow="incident log"
        title="Live incident stream"
        description="Realtime incident state is merged from the list endpoint, SSE updates, and periodic reconciliation."
      />
      <div className="min-h-0 flex-1 space-y-3 overflow-auto px-4 py-4 sm:px-5">
        {incidents.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-10 text-center">
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-slate-500">
              No incidents detected
            </p>
            <p className="mt-3 text-sm text-slate-300">
              The dashboard will populate once the backend returns incident data.
            </p>
          </div>
        ) : null}

        {incidents.map((incident) => {
          const active = incident.incident_id === selectedIncidentId;
          const updatedAt = incident.updated_at_ms ?? incident.created_at_ms;

          return (
            <button
              key={incident.incident_id}
              type="button"
              onClick={() => onSelect(incident.incident_id)}
              className={`w-full rounded-2xl border p-4 text-left transition ${
                active
                  ? "border-cyan-300/55 bg-cyan-300/10 shadow-[0_0_0_1px_rgba(0,212,255,0.15)]"
                  : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={incident.severity} />
                    <span className="font-mono text-xs uppercase tracking-[0.24em] text-slate-400">
                      {shortId(incident.incident_id)}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-white">
                    {incident.service} / {incident.environment}
                  </p>
                </div>
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-slate-500">
                  {formatRelativeTime(updatedAt)}
                </span>
              </div>

              <div className="mt-4 space-y-2 text-sm">
                <StatusBadge status={incident.status} />
                <p className="truncate text-slate-300">
                  {incident.source.error_type}: {incident.source.error_message}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}
