"use client";

import Link from "next/link";

import { useBackendHealth } from "../dashboard/hooks/useBackendHealth";
import { useIncidents } from "../dashboard/hooks/useIncidents";
import type { HealthResponse, Incident, IncidentTimelineEvent } from "../dashboard/types";

const sponsorLinks = ["Airbyte", "Aerospike", "Macroscope", "Kiro", "Auth0", "Bland AI"] as const;
const sideLinks: Array<{
  href: string;
  label: string;
  mark: string;
  active?: boolean;
}> = [
  { href: "/dashboard", label: "Incidents", mark: "IN" },
  { href: "/metrics", label: "Metrics", mark: "MX", active: true },
  { href: "/dashboard", label: "Logs", mark: "LG" },
  { href: "/settings", label: "Settings", mark: "ST" },
];

const sponsorColors = {
  ingest: "#634BFF",
  store: "#C4302B",
  diagnose: "#00DAF3",
  fix: "#FFB44C",
  gate: "#EB5424",
  escalate: "#FFFFFF",
  deploy: "#10B981",
  optimize: "#A855F7",
} as const;

function avg(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function formatClock(timestampMs: number) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(timestampMs);
}

function resolutionMetrics(incidents: Incident[]) {
  const resolved = incidents.filter(
    (incident) =>
      incident.status === "resolved" &&
      typeof incident.resolution_time_ms === "number" &&
      incident.resolution_time_ms > 0,
  );
  const mttrMs = avg(resolved.map((incident) => incident.resolution_time_ms ?? 0));
  const autoResolved = incidents.filter(
    (incident) =>
      incident.status === "resolved" &&
      (!incident.approval.required || incident.approval.status !== "pending"),
  ).length;

  return {
    mttrMinutes: mttrMs ? (mttrMs / 60_000).toFixed(1) : "0.0",
    autoHealRate: resolved.length ? ((autoResolved / resolved.length) * 100).toFixed(1) : "0.0",
    approvalRate: incidents.length
      ? (
          (incidents.filter((incident) => incident.approval.required).length / incidents.length) *
          100
        ).toFixed(1)
      : "0.0",
    criticalOpen: incidents.filter(
      (incident) => incident.severity === "critical" && incident.status !== "resolved",
    ).length,
    resolvedCount: resolved.length,
  };
}

function timeBuckets(incidents: Incident[]) {
  const now = Date.now();
  const bucketSizeMs = 3 * 60 * 60 * 1000;

  return Array.from({ length: 8 }, (_, index) => {
    const end = now - (7 - index) * bucketSizeMs;
    const start = end - bucketSizeMs;
    const count = incidents.filter((incident) => {
      const timestamp = incident.updated_at_ms ?? incident.created_at_ms;
      return timestamp >= start && timestamp < end;
    }).length;

    return {
      label: new Intl.DateTimeFormat("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(end),
      count,
    };
  });
}

function buildLine(values: number[], width: number, height: number) {
  const max = Math.max(...values, 1);
  const step = width / Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      const x = index * step;
      const y = height - (value / max) * (height - 24) - 12;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function stageBuckets(incidents: Incident[]) {
  return [
    ["Ingest", incidents.filter((incident) => incident.status === "detected").length, sponsorColors.ingest],
    ["Store", incidents.filter((incident) => incident.status === "stored").length, sponsorColors.store],
    ["Diagnose", incidents.filter((incident) => incident.status === "diagnosing").length, sponsorColors.diagnose],
    ["Fix", incidents.filter((incident) => incident.status === "fixing").length, sponsorColors.fix],
    ["Gate", incidents.filter((incident) => incident.status === "gating").length, sponsorColors.gate],
    ["Approve", incidents.filter((incident) => incident.status === "awaiting_approval").length, sponsorColors.gate],
    ["Deploy", incidents.filter((incident) => incident.status === "deploying").length, sponsorColors.deploy],
    ["Resolved", incidents.filter((incident) => incident.status === "resolved").length, sponsorColors.optimize],
  ] as const;
}

function serviceRows(incidents: Incident[], health: HealthResponse | null, backendOk: boolean) {
  const pendingApprovals = incidents.filter(
    (incident) =>
      incident.status === "awaiting_approval" && incident.approval.status === "pending",
  ).length;
  const criticalEscalations = incidents.filter(
    (incident) =>
      incident.severity === "critical" &&
      incident.status === "awaiting_approval" &&
      incident.approval.status === "pending",
  ).length;
  const failedDeploys = incidents.filter((incident) => incident.deployment?.status === "failed").length;
  const activeDeploys = incidents.filter((incident) => incident.status === "deploying").length;

  return [
    ["deepops-api", backendOk ? "Live" : "Degraded", sponsorColors.ingest, backendOk ? "up" : "warn"],
    ["aerospike-store", health?.store ?? "unknown", sponsorColors.store, health?.store === "aerospike" ? "up" : "warn"],
    ["macroscope-diagnoser", incidents.some((incident) => incident.status === "diagnosing") ? "Active" : "Stable", sponsorColors.diagnose, incidents.filter((incident) => incident.status === "diagnosing").length > 2 ? "warn" : "up"],
    ["kiro-fix-engine", incidents.some((incident) => incident.fix.status === "failed") ? "Warn" : "Healthy", sponsorColors.fix, incidents.some((incident) => incident.fix.status === "failed") ? "warn" : "up"],
    ["auth0-approval-gate", pendingApprovals ? `${pendingApprovals} pending` : "Clear", sponsorColors.gate, pendingApprovals ? "warn" : "up"],
    ["bland-voice-relay", criticalEscalations ? `${criticalEscalations} queued` : "Standby", sponsorColors.escalate, criticalEscalations ? "warn" : "up"],
    ["truefoundry-deploy", failedDeploys ? `${failedDeploys} failed` : activeDeploys ? `${activeDeploys} active` : "Stable", sponsorColors.deploy, failedDeploys ? "down" : activeDeploys ? "warn" : "up"],
    ["overmind-trace-loop", "Trace path ready", sponsorColors.optimize, backendOk ? "up" : "warn"],
  ] as const;
}

function timelineFeed(incidents: Incident[]) {
  return incidents
    .flatMap((incident) =>
      incident.timeline.map((event) => ({
        incidentId: incident.incident_id,
        title: incident.title ?? incident.source.error_type,
        event,
      })),
    )
    .sort((left, right) => right.event.at_ms - left.event.at_ms)
    .slice(0, 8);
}

function feedTone(event: IncidentTimelineEvent) {
  const sponsor = (event.sponsor ?? "").toLowerCase();
  if (sponsor.includes("truefoundry") || event.status.includes("deploy")) return "text-[#10B981]";
  if (sponsor.includes("overmind")) return "text-[#A855F7]";
  if (sponsor.includes("bland")) return "text-white";
  if (event.status.includes("failed") || event.status.includes("blocked")) return "text-[#FFB4AB]";
  return "text-[#634BFF]";
}

export default function MetricsPage() {
  const { incidents, isLoading, isRefreshing, error, streamState } = useIncidents();
  const { health, status: backendStatus, lastCheckedAt, error: healthError } = useBackendHealth();
  const metrics = resolutionMetrics(incidents);
  const buckets = timeBuckets(incidents);
  const counts = buckets.map((bucket) => bucket.count);
  const linePath = buildLine(counts, 1000, 300);
  const areaPath = `${linePath} L 1000 300 L 0 300 Z`;
  const stages = stageBuckets(incidents);
  const stageMax = Math.max(...stages.map(([, count]) => count), 1);
  const rows = serviceRows(incidents, health, backendStatus === "live");
  const feed = timelineFeed(incidents);
  const footer =
    healthError ??
    error ??
    (isLoading
      ? "Bootstrapping metrics from the incident stream."
      : isRefreshing
        ? "Refreshing incident aggregates."
        : `Incident feed ${streamState}. Last health check ${lastCheckedAt ? formatClock(lastCheckedAt) : "pending"}.`);

  return (
    <main className="min-h-screen bg-black text-[#E1E2EB]">
      <nav className="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-[#222222] bg-black px-6">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-display text-2xl font-bold uppercase tracking-[-0.05em] text-white">
            DeepOps
          </Link>
          <div className="hidden items-center gap-6 font-display text-[11px] font-bold uppercase tracking-tight md:flex">
            {sponsorLinks.map((link) => (
              <span key={link} className="text-white/40 transition-colors hover:text-[#634BFF]">
                {link}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4 text-white/55">
          <button className="p-2 font-mono text-xs hover:text-[#634BFF]">SN</button>
          <button className="p-2 font-mono text-xs hover:text-[#634BFF]">AL</button>
          <button className="p-2 font-mono text-xs hover:text-[#634BFF]">ME</button>
        </div>
      </nav>

      <aside className="fixed top-0 left-0 hidden h-full w-64 flex-col border-r border-[#222222] bg-black py-8 md:flex">
        <div className="mt-12 mb-10 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-[#121212] font-display text-sm font-bold uppercase tracking-tight text-white">
              DO
            </div>
            <div>
              <h3 className="font-display text-sm font-bold tracking-tight text-white">DeepOps Control</h3>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/45">NOC-01 Terminal</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {sideLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-xs font-semibold transition-all ${
                link.active ? "border-r-2 border-[#634BFF] bg-[#050505] text-[#634BFF]" : "text-white/52 hover:bg-[#050505] hover:text-white"
              }`}
            >
              <span className="font-mono text-[10px]">{link.mark}</span>
              <span>{link.label}</span>
            </Link>
          ))}
        </nav>

        <div className="mt-auto space-y-1 border-t border-white/6 px-3 pt-8">
          <Link href="/" className="flex items-center gap-3 rounded-lg px-4 py-3 text-xs font-semibold text-white/52 hover:bg-[#050505] hover:text-white">
            <span className="font-mono text-[10px]">DC</span>
            <span>Documentation</span>
          </Link>
          <Link href="/dashboard" className="flex items-center gap-3 rounded-lg px-4 py-3 text-xs font-semibold text-white/52 hover:bg-[#050505] hover:text-white">
            <span className="font-mono text-[10px]">SP</span>
            <span>Support</span>
          </Link>
        </div>
      </aside>

      <div className="min-h-screen bg-black pt-20 md:pl-64">
        <div className="mx-auto max-w-[1600px] p-6 lg:p-10">
          <header className="mb-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="h-1 w-8 rounded-full bg-[#634BFF]" />
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#634BFF]">Operational Overview</span>
              </div>
              <h1 className="font-display text-4xl font-bold tracking-[-0.05em] text-white md:text-5xl">
                Codebase Health <span className="text-white/22">&amp;</span> Metrics
              </h1>
            </div>
            <div className="flex gap-3">
              <button className="rounded-xl border border-[#333333] bg-[#0A0A0A] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#1A1A1A]">
                Export
              </button>
              <button className="rounded-xl bg-[#634BFF] px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-[#634BFF]/20 hover:opacity-90">
                Live Sync
              </button>
            </div>
          </header>

          <div className="mb-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <div className="relative overflow-hidden rounded-xl border border-white/8 bg-[#0A0A0A] p-6">
              <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(99,75,255,0.05)_0%,rgba(0,218,243,0.02)_100%)]" />
              <div className="relative z-10">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/46">
                  MTTR (Mean Time To Resolution)
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <span className="font-display text-5xl font-bold tracking-[-0.06em] text-[#634BFF]">
                    {metrics.mttrMinutes}
                  </span>
                  <span className="font-display text-xl text-white/52">m</span>
                </div>
                <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/44">
                  {metrics.resolvedCount} resolved incidents observed
                </div>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-xl border border-white/8 bg-[#0A0A0A] p-6">
              <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(99,75,255,0.05)_0%,rgba(0,218,243,0.02)_100%)]" />
              <div className="relative z-10">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/46">
                  Autonomous Resolution Rate
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <span className="font-display text-5xl font-bold tracking-[-0.06em] text-[#00DAF3]">
                    {metrics.autoHealRate}
                  </span>
                  <span className="font-display text-xl text-white/52">%</span>
                </div>
                <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/44">
                  Resolved without a pending human gate
                </div>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-xl border border-white/8 bg-[#0A0A0A] p-6">
              <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(99,75,255,0.05)_0%,rgba(0,218,243,0.02)_100%)]" />
              <div className="relative z-10">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/46">
                  Approval Required Rate
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <span className="font-display text-5xl font-bold tracking-[-0.06em] text-[#FFB4AB]">
                    {metrics.approvalRate}
                  </span>
                  <span className="font-display text-xl text-white/52">%</span>
                </div>
                <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/44">
                  Share of incidents entering approval
                </div>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-xl border border-white/8 bg-[#0A0A0A] p-6">
              <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(99,75,255,0.05)_0%,rgba(0,218,243,0.02)_100%)]" />
              <div className="relative z-10">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-white/46">
                  Critical Incidents Open
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <span className="font-display text-5xl font-bold tracking-[-0.06em] text-white">
                    {metrics.criticalOpen}
                  </span>
                </div>
                <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/44">
                  Backend {backendStatus.toUpperCase()} / store {health?.store ?? "unknown"}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-12 rounded-xl border border-[#222222] bg-[#0A0A0A] p-8 lg:col-span-8">
              <div className="mb-10 flex items-start justify-between">
                <div>
                  <h3 className="font-display text-xl font-bold tracking-tight text-white">
                    Incidents over Time
                  </h3>
                  <p className="mt-1 text-xs text-white/45">
                    Rolling incident volume from the live stream and reconciliation loop
                  </p>
                </div>
                <div className="flex gap-2">
                  <span className="rounded-full border border-[#634BFF]/20 bg-[#121212] px-3 py-1 font-mono text-[10px] text-[#634BFF]">
                    {streamState.toUpperCase()}
                  </span>
                  <span className="rounded-full bg-[#121212] px-3 py-1 font-mono text-[10px] text-white/50">
                    24H
                  </span>
                </div>
              </div>

              <div className="relative h-[300px] w-full border-b border-white/8 pb-6">
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 300" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="metricsLineGradient" x1="0%" x2="0%" y1="0%" y2="100%">
                      <stop offset="0%" stopColor="#634BFF" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#634BFF" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  {linePath ? <path d={areaPath} fill="url(#metricsLineGradient)" /> : null}
                  {linePath ? (
                    <path
                      d={linePath}
                      fill="none"
                      stroke="#634BFF"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                  ) : null}
                </svg>
                <div className="pointer-events-none absolute inset-0 flex flex-col justify-between opacity-10">
                  <div className="border-t border-white" />
                  <div className="border-t border-white" />
                  <div className="border-t border-white" />
                  <div className="border-t border-white" />
                </div>
              </div>

              <div className="mt-4 flex justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-white/42">
                {buckets.map((bucket) => (
                  <span key={bucket.label}>{bucket.label}</span>
                ))}
              </div>
            </div>

            <div className="col-span-12 flex flex-col overflow-hidden rounded-xl border border-[#222222] bg-[#0A0A0A] lg:col-span-4">
              <div className="border-b border-[#222222] p-6">
                <h3 className="font-display text-sm font-bold uppercase tracking-[0.14em] text-white">
                  Service Health
                </h3>
              </div>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {rows.map(([label, detail, color, tone]) => (
                  <div
                    key={label}
                    className="group flex items-center justify-between rounded-lg border border-white/8 bg-black px-3 py-3 transition-colors hover:border-[#634BFF]/50"
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          tone === "up"
                            ? "bg-[#00DAF3] shadow-[0_0_8px_rgba(0,218,243,0.6)]"
                            : tone === "warn"
                              ? "bg-[#FFB4AB] shadow-[0_0_8px_rgba(255,180,171,0.55)]"
                              : "bg-[#FF4B4B] shadow-[0_0_8px_rgba(255,75,75,0.55)]"
                        }`}
                      />
                      <span className="font-mono text-xs font-medium" style={{ color }}>
                        {label}
                      </span>
                    </div>
                    <span
                      className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase ${
                        tone === "up"
                          ? "border-white/10 bg-[#1A1A1A] text-white/58"
                          : tone === "warn"
                            ? "border-[#FFB4AB]/20 text-[#FFB4AB]"
                            : "border-[#FF4B4B]/20 text-[#FF4B4B]"
                      }`}
                    >
                      {detail}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-span-12 rounded-xl border border-[#222222] bg-[#0A0A0A] p-8">
              <div className="mb-8">
                <h3 className="font-display text-xl font-bold tracking-tight text-white">
                  Incidents by Sponsor Pipeline Stage
                </h3>
                <p className="mt-1 text-xs text-white/45">
                  Breakdown by the real DeepOps remediation stages
                </p>
              </div>

              <div className="grid h-52 grid-cols-2 gap-6 md:grid-cols-4 xl:grid-cols-8">
                {stages.map(([label, count, color]) => (
                  <div key={label} className="group flex h-full flex-col items-center gap-4">
                    <div className="flex h-full w-full items-end">
                      <div
                        className="w-full rounded-t-lg transition-all group-hover:brightness-110"
                        style={{
                          height: `${Math.max(12, Math.round((count / stageMax) * 100))}%`,
                          backgroundColor: color,
                          boxShadow: count > 0 ? `0 0 20px ${color}44` : "none",
                          opacity: count > 0 ? 1 : 0.25,
                        }}
                      />
                    </div>
                    <div className="text-center">
                      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
                        {label}
                      </div>
                      <div className="mt-2 font-display text-lg font-bold tracking-tight" style={{ color }}>
                        {count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-12 overflow-hidden rounded-xl border border-[#222222] bg-black">
            <div className="flex items-center justify-between border-b border-[#222222] bg-[#0A0A0A] px-6 py-4">
              <span className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-white/45">
                Live Data Stream [Overmind-01]
              </span>
              <div className="flex items-center gap-3">
                <div className="h-2 w-2 rounded-full bg-[#00DAF3] shadow-[0_0_8px_rgba(0,218,243,0.5)]" />
                <span className="font-mono text-[10px] uppercase text-[#00DAF3]">Synced</span>
              </div>
            </div>
            <div className="max-h-56 space-y-2 overflow-y-auto p-6 font-mono text-[11px] leading-relaxed">
              {feed.length === 0 ? (
                <div className="opacity-60">No incident timeline events have been observed yet.</div>
              ) : (
                feed.map((item) => (
                  <div key={`${item.incidentId}-${item.event.at_ms}-${item.event.message}`} className="flex gap-4">
                    <span className="min-w-24 text-white/40">{formatClock(item.event.at_ms)}</span>
                    <span className={`font-bold ${feedTone(item.event)}`}>
                      [{(item.event.sponsor ?? item.event.actor ?? item.event.status).toUpperCase()}]
                    </span>
                    <span className="text-white/74">
                      {item.incidentId} · {item.title} · {item.event.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-8 rounded-xl border border-white/8 bg-[#0A0A0A] px-5 py-4 font-mono text-xs uppercase tracking-[0.18em] text-white/42">
            {footer}
          </div>
        </div>
      </div>

      <button className="fixed right-8 bottom-8 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-[#634BFF] text-white shadow-2xl transition-all hover:scale-110 active:scale-95">
        <span className="text-3xl leading-none">+</span>
      </button>
    </main>
  );
}
