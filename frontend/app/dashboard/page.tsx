"use client";

import { ApprovalButtons } from "./components/ApprovalButtons";
import { DashboardHeader } from "./components/dashboard-header";
import { DiffViewer } from "./components/DiffViewer";
import { IncidentList } from "./components/IncidentList";
import { Metric, Panel, Pill } from "./components/dashboard-ui";
import { useApproval } from "./hooks/useApproval";
import { useBackendHealth } from "./hooks/useBackendHealth";
import { useIncidents } from "./hooks/useIncidents";

function mapConnectionState(status: "loading" | "live" | "degraded" | "offline") {
  if (status === "live") {
    return "LIVE" as const;
  }

  if (status === "offline") {
    return "OFFLINE" as const;
  }

  return "DEGRADED" as const;
}

function formatOverviewCount(
  incidents: Array<{ status: string; approval: { status: string }; severity: string }>,
) {
  const open = incidents.filter((incident) => incident.status !== "resolved").length;
  const awaiting = incidents.filter(
    (incident) =>
      incident.status === "awaiting_approval" &&
      incident.approval.status === "pending",
  ).length;
  const critical = incidents.filter((incident) => incident.severity === "critical").length;
  return { open, awaiting, critical };
}

export default function DashboardPage() {
  const {
    incidents,
    selectedIncidentId,
    selectedIncident,
    isLoading,
    isRefreshing,
    error: incidentsError,
    streamState,
    setSelectedIncidentId,
    replaceIncident,
    refreshIncidents,
    refreshSelectedIncident,
  } = useIncidents({ autoSelectFirst: true });
  const {
    approve,
    reject,
    isSubmitting,
    error: approvalError,
    clearError: clearApprovalError,
  } = useApproval();
  const {
    health,
    status: healthStatus,
    error: healthError,
    lastCheckedAt,
  } = useBackendHealth();

  const { open, awaiting, critical } = formatOverviewCount(incidents);

  const handleSelect = (incidentId: string) => {
    clearApprovalError();
    setSelectedIncidentId(incidentId);
    void refreshSelectedIncident(incidentId);
  };

  const handleApprove = async () => {
    if (!selectedIncident) {
      return;
    }

    try {
      const response = await approve(selectedIncident.incident_id);
      replaceIncident(response.incident);
      await refreshSelectedIncident(response.incident.incident_id);
      await refreshIncidents({ background: true });
    } catch {
      // Error state is exposed by useApproval.
    }
  };

  const handleReject = async () => {
    if (!selectedIncident) {
      return;
    }

    try {
      const response = await reject(selectedIncident.incident_id);
      replaceIncident(response.incident);
      await refreshSelectedIncident(response.incident.incident_id);
      await refreshIncidents({ background: true });
    } catch {
      // Error state is exposed by useApproval.
    }
  };

  const footerMessage =
    approvalError ??
    incidentsError ??
    healthError ??
    (isLoading
      ? "Loading incidents from the backend."
      : isRefreshing
        ? "Refreshing incident state."
        : streamState === "degraded"
          ? "SSE stream is reconnecting. Periodic polling is keeping the list aligned."
          : "SSE stream and periodic reconciliation are active.");

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(0,212,255,0.14),_transparent_26%),linear-gradient(180deg,#0a1628_0%,#07111e_100%)] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8">
        <Panel className="overflow-hidden">
          <DashboardHeader connectionState={mapConnectionState(healthStatus)} />
          <div className="grid gap-4 px-5 py-5 sm:px-6 lg:grid-cols-3">
            <Metric
              label="incident count"
              value={`${incidents.length} tracked incidents`}
            />
            <Metric label="open incidents" value={`${open} requiring attention`} />
            <Metric label="approval queue" value={`${awaiting} awaiting human decision`} />
          </div>
          <div className="grid gap-4 border-t border-white/10 px-5 py-4 sm:px-6 lg:grid-cols-3">
            <Metric label="critical severity" value={`${critical} critical cases`} />
            <Metric
              label="backend"
              value={`${health?.backend ?? "fastapi"} / ${health?.environment ?? "unknown"}`}
            />
            <Metric
              label="last health check"
              value={
                lastCheckedAt
                  ? new Intl.DateTimeFormat("en", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    }).format(lastCheckedAt)
                  : "pending"
              }
            />
          </div>
        </Panel>

        <div className="mt-4 grid flex-1 gap-4 lg:grid-cols-[0.92fr_1.08fr]">
          <IncidentList
            incidents={incidents}
            selectedIncidentId={selectedIncidentId}
            onSelect={handleSelect}
          />

          <div className="grid min-h-0 gap-4">
            <DiffViewer incident={selectedIncident ?? null} />
            <ApprovalButtons
              incident={selectedIncident ?? null}
              isSubmitting={isSubmitting}
              error={approvalError}
              onApprove={() => {
                void handleApprove();
              }}
              onReject={() => {
                void handleReject();
              }}
            />
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 font-mono text-xs uppercase tracking-[0.24em] text-slate-400">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{footerMessage}</span>
            <div className="flex flex-wrap gap-2">
              <Pill tone="cyan">{streamState}</Pill>
              <Pill
                tone={
                  healthStatus === "live"
                    ? "green"
                    : healthStatus === "offline"
                      ? "red"
                      : "orange"
                }
              >
                {mapConnectionState(healthStatus)}
              </Pill>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
