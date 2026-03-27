"use client";

import { useState } from "react";
import Link from "next/link";
import { useApproval } from "./hooks/useApproval";
import { useBackendHealth } from "./hooks/useBackendHealth";
import { useIncidents } from "./hooks/useIncidents";
import type { Incident, IncidentStatus, IncidentTimelineEvent } from "./types";

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

const SPONSORS = [
  { name: "Airbyte", color: "#634BFF" },
  { name: "Aerospike", color: "#C4302B" },
  { name: "Macroscope", color: "#00B4D8" },
  { name: "Kiro", color: "#FF9900" },
  { name: "Auth0", color: "#EB5424" },
  { name: "Bland AI", color: "#6366F1" },
  { name: "TrueFoundry", color: "#10B981" },
  { name: "Overmind", color: "#A855F7" },
];

const PIPELINE_STAGES: {
  key: string;
  label: string;
  color: string;
  sponsor: string;
  icon: string;
}[] = [
  { key: "detected", label: "Detected", color: "#F87171", sponsor: "Airbyte", icon: "🔄" },
  { key: "stored", label: "Stored", color: "#C4302B", sponsor: "Aerospike", icon: "⚡" },
  { key: "diagnosing", label: "Diagnosing", color: "#00B4D8", sponsor: "Macroscope", icon: "🔍" },
  { key: "fixing", label: "Fixing", color: "#FF9900", sponsor: "Kiro", icon: "👻" },
  { key: "gating", label: "Auth Check", color: "#EB5424", sponsor: "Auth0", icon: "🔐" },
  { key: "awaiting_approval", label: "Calling...", color: "#6366F1", sponsor: "Bland AI", icon: "📞" },
  { key: "deploying", label: "Deploying", color: "#10B981", sponsor: "TrueFoundry", icon: "🚀" },
  { key: "resolved", label: "Resolved", color: "#22C55E", sponsor: "Overmind", icon: "⚙️" },
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#FF4B66",
  high: "#FF9900",
  medium: "#FDE68A",
  low: "#10B981",
  pending: "#A9ABB3",
};

const NAV_ITEMS = [
  { label: "Incidents", icon: "emergency_home", href: "/dashboard" },
  { label: "Metrics", icon: "insert_chart", href: "/metrics" },
  { label: "Agent Logs", icon: "terminal", href: "#" },
  { label: "Overmind Traces", icon: "visibility", href: "#" },
  { label: "Settings", icon: "settings", href: "/settings" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function shortId(id: string) {
  return id.length > 10 ? `${id.slice(0, 4)}...${id.slice(-4)}` : id;
}

function timeAgo(ms: number): string {
  const diff = Math.max(0, Date.now() - ms);
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function formatTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function getPipelineStageIndex(status: IncidentStatus): number {
  const idx = PIPELINE_STAGES.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : -1;
}

type DiffLine = {
  kind: "header" | "add" | "remove" | "context";
  text: string;
};

function parseDiff(diffPreview: string | null): DiffLine[] {
  if (!diffPreview) return [];
  return diffPreview.split("\n").map((line) => {
    if (line.startsWith("@@") || line.startsWith("+++") || line.startsWith("---"))
      return { kind: "header", text: line };
    if (line.startsWith("+")) return { kind: "add", text: line };
    if (line.startsWith("-")) return { kind: "remove", text: line };
    return { kind: "context", text: line };
  });
}

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */

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

  const [triggerLoading, setTriggerLoading] = useState(false);

  /* -- Handlers ---------------------------------------------------- */

  const handleSelect = (incidentId: string) => {
    clearApprovalError();
    setSelectedIncidentId(incidentId);
    void refreshSelectedIncident(incidentId);
  };

  const handleApprove = async () => {
    if (!selectedIncident) return;
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
    if (!selectedIncident) return;
    try {
      const response = await reject(selectedIncident.incident_id);
      replaceIncident(response.incident);
      await refreshSelectedIncident(response.incident.incident_id);
      await refreshIncidents({ background: true });
    } catch {
      // Error state is exposed by useApproval.
    }
  };

  const triggerBug = async () => {
    setTriggerLoading(true);
    try {
      const bugs = ["calculate_zero", "user_missing", "search_timeout"];
      const key = bugs[Math.floor(Math.random() * bugs.length)];
      const res = await fetch("/api/ingest/demo-trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bug_key: key }),
      });
      const data = await res.json();
      const incidentId = data?.incident?.incident_id;
      if (incidentId) {
        await fetch(`/api/agent/run-once?incident_id=${incidentId}`, {
          method: "POST",
        });
      }
      refreshIncidents();
    } catch {
      // silently ignore
    } finally {
      setTriggerLoading(false);
    }
  };

  /* -- Metrics from real data -------------------------------------- */

  const activeCount = incidents.filter(
    (i) => i.status !== "resolved" && i.status !== "blocked" && i.status !== "failed",
  ).length;
  const resolvedCount = incidents.filter((i) => i.status === "resolved").length;
  const awaitingCount = incidents.filter((i) => i.status === "awaiting_approval").length;

  const resolvedIncidents = incidents.filter((i) => i.resolution_time_ms);
  const avgResolutionMs =
    resolvedIncidents.length > 0
      ? resolvedIncidents.reduce((sum, i) => sum + (i.resolution_time_ms ?? 0), 0) /
        resolvedIncidents.length
      : 0;
  const avgResolutionSec = Math.round(avgResolutionMs / 1000);

  /* -- Pipeline from selected incident ----------------------------- */

  const currentStageIdx = selectedIncident ? getPipelineStageIndex(selectedIncident.status) : -1;

  /* -- Agent logs from timeline ------------------------------------ */

  const allTimelineEvents: (IncidentTimelineEvent & { incident_id: string })[] = incidents
    .flatMap((i) => i.timeline.map((e) => ({ ...e, incident_id: i.incident_id })))
    .sort((a, b) => b.at_ms - a.at_ms)
    .slice(0, 20);

  /* -- Awaiting approval incident for Bland AI card ---------------- */

  const awaitingIncident =
    selectedIncident?.status === "awaiting_approval"
      ? selectedIncident
      : incidents.find((i) => i.status === "awaiting_approval") ?? null;

  /* -- Diff lines -------------------------------------------------- */

  const diffLines = selectedIncident ? parseDiff(selectedIncident.fix.diff_preview) : [];

  /* -- Connection badge -------------------------------------------- */

  const isConnected = healthStatus === "live" || streamState === "live";

  /* -- Pad numbers ------------------------------------------------- */

  function pad2(n: number): string {
    return n.toString().padStart(2, "0");
  }

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <>
      {/* ============================================================ */}
      {/* SIDEBAR                                                       */}
      {/* ============================================================ */}
      <aside className="fixed left-0 top-0 h-full flex flex-col py-6 bg-black w-64 border-r border-white/[0.08] z-50">
        <div className="px-6 mb-10">
          <h1 className="text-2xl font-bold tracking-tighter text-white font-display">
            DeepOps
          </h1>
          <p className="font-display text-[10px] uppercase tracking-widest text-white/40">
            Mission Control
          </p>
        </div>

        <nav className="flex-1 px-4 space-y-2">
          {NAV_ITEMS.map((item) => {
            const isActive = item.href === "/dashboard";
            const classes = `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? "text-[#634BFF] border-l-2 border-[#634BFF] bg-[#634BFF]/5"
                : "text-white/50 hover:text-white hover:bg-white/5"
            }`;

            if (item.href === "#") {
              return (
                <a key={item.label} href="#" className={classes}>
                  <span className="material-symbols-outlined">{item.icon}</span>
                  <span>{item.label}</span>
                </a>
              );
            }

            return (
              <Link key={item.label} href={item.href} className={classes}>
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="px-4 mt-auto">
          <button
            onClick={() => void triggerBug()}
            disabled={triggerLoading}
            className="w-full py-4 px-6 rounded-xl bg-gradient-to-br from-[#FF4B66] to-[#8A1F30] text-white font-display font-bold tracking-tight shadow-lg shadow-[#FF4B66]/20 active:scale-95 transition-transform duration-100 disabled:opacity-60"
            style={{
              animation: "pulse-high 2s cubic-bezier(0.4,0,0.6,1) infinite",
            }}
          >
            {triggerLoading ? "TRIGGERING..." : "TRIGGER BUG"}
          </button>
          <div className="mt-6 flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-[#634BFF]">person</span>
            </div>
            <div>
              <p className="text-xs font-bold text-white">Active Engineer</p>
              <p className="text-[10px] text-white/40 uppercase">
                SRE-01 &bull; ON-CALL
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* ============================================================ */}
      {/* MAIN CONTENT                                                  */}
      {/* ============================================================ */}
      <main className="ml-64 min-h-screen flex flex-col">
        {/* ---------------------------------------------------------- */}
        {/* TOP BAR                                                      */}
        {/* ---------------------------------------------------------- */}
        <header className="sticky top-0 w-full flex justify-between items-center px-8 h-16 bg-black/80 backdrop-blur-xl z-40 border-b border-white/[0.08]">
          <div className="flex items-center gap-6">
            {SPONSORS.map((s) => (
              <span
                key={s.name}
                className="font-display uppercase tracking-widest text-[10px] font-bold cursor-pointer hover:opacity-80 transition-opacity"
                style={{ color: s.color }}
              >
                {s.name}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-6">
            <div
              className={`flex items-center gap-2 px-3 py-1 rounded-full border ${
                isConnected
                  ? "bg-[#10B981]/10 border-[#10B981]/20"
                  : "bg-[#FF4B66]/10 border-[#FF4B66]/20"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-[#10B981]" : "bg-[#FF4B66]"
                }`}
              />
              <span
                className={`text-[10px] font-display uppercase font-bold ${
                  isConnected ? "text-[#10B981]" : "text-[#FF4B66]"
                }`}
              >
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <span className="material-symbols-outlined text-xl text-white/50 cursor-pointer hover:text-[#634BFF] transition-colors">
              notifications
            </span>
          </div>
        </header>

        {/* ---------------------------------------------------------- */}
        {/* GRID CONTENT                                                 */}
        {/* ---------------------------------------------------------- */}
        <div className="p-8 grid grid-cols-12 gap-8">
          {/* ======================================================== */}
          {/* METRICS ROW                                                */}
          {/* ======================================================== */}
          <section className="col-span-12 grid grid-cols-4 gap-6 mb-2">
            <div className="bg-[#0A0A0B] rounded-xl p-4 flex flex-col border border-white/[0.08]">
              <span className="text-[10px] font-display uppercase tracking-widest text-white/50 mb-1">
                Active Incidents
              </span>
              <span className="text-3xl font-display font-bold text-[#FF4B66]">
                {pad2(activeCount)}
              </span>
            </div>
            <div className="bg-[#0A0A0B] rounded-xl p-4 flex flex-col border border-white/[0.08]">
              <span className="text-[10px] font-display uppercase tracking-widest text-white/50 mb-1">
                Auto-Resolved
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-display font-bold text-[#10B981]">
                  {pad2(resolvedCount)}
                </span>
                <span className="text-xs text-[#10B981]/60">
                  of {incidents.length}
                </span>
              </div>
            </div>
            <div className="bg-[#0A0A0B] rounded-xl p-4 flex flex-col border border-white/[0.08]">
              <span className="text-[10px] font-display uppercase tracking-widest text-white/50 mb-1">
                Avg Resolution
              </span>
              <span className="text-3xl font-display font-bold">
                {avgResolutionSec > 0 ? avgResolutionSec : "--"}
                <span className="text-lg font-light text-white/50 ml-1">sec</span>
              </span>
            </div>
            <div className="bg-[#0A0A0B] rounded-xl p-4 flex flex-col border border-white/[0.08]">
              <span className="text-[10px] font-display uppercase tracking-widest text-white/50 mb-1">
                Awaiting Approval
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-display font-bold" style={{ color: "#6366F1" }}>
                  {pad2(awaitingCount)}
                </span>
                <span className="text-[10px] text-white/40 font-mono">via Bland AI</span>
              </div>
            </div>
          </section>

          {/* ======================================================== */}
          {/* LEFT COLUMN                                                */}
          {/* ======================================================== */}
          <div className="col-span-12 lg:col-span-7 space-y-8">
            {/* ---- Incident Cards ---------------------------------- */}
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.2em] text-white/50 mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF4B66]" />
                Active Incidents
              </h2>

              {isLoading && incidents.length === 0 ? (
                <div className="bg-[#0A0A0B] rounded-2xl p-6 border border-white/[0.08] text-center">
                  <p className="text-sm text-white/50">Loading incidents...</p>
                </div>
              ) : incidents.length === 0 ? (
                <div className="bg-[#0A0A0B] rounded-2xl p-6 border border-dashed border-white/[0.08] text-center">
                  <p className="text-sm text-white/50">No incidents detected</p>
                  <p className="text-xs text-white/30 mt-2">
                    Press TRIGGER BUG to inject a demo incident.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {incidents.map((incident) => {
                    const isSelected = incident.incident_id === selectedIncidentId;
                    const isResolved = incident.status === "resolved";
                    const sevColor = SEVERITY_COLORS[incident.severity] ?? "#A9ABB3";
                    const updatedAt = incident.updated_at_ms ?? incident.created_at_ms;

                    return (
                      <button
                        key={incident.incident_id}
                        type="button"
                        onClick={() => handleSelect(incident.incident_id)}
                        className={`w-full text-left rounded-2xl p-6 border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-[#121214] border-l-4 shadow-2xl"
                            : isResolved
                              ? "bg-[#0A0A0B] border-white/[0.08] opacity-60 hover:opacity-100"
                              : "bg-[#0A0A0B] border-white/[0.08] hover:border-white/20"
                        }`}
                        style={{
                          borderLeftColor: isSelected ? sevColor : undefined,
                        }}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-3">
                            <span
                              className="font-mono text-xs px-2 py-0.5 rounded"
                              style={{
                                color: isSelected ? sevColor : "#A9ABB3",
                                backgroundColor: isSelected
                                  ? `${sevColor}15`
                                  : "transparent",
                              }}
                            >
                              {shortId(incident.incident_id)}
                            </span>
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest"
                              style={{
                                color: sevColor,
                                backgroundColor: `${sevColor}15`,
                              }}
                            >
                              {incident.severity}
                            </span>
                            {isResolved && (
                              <span className="px-2 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] text-[10px] font-bold uppercase tracking-widest">
                                RESOLVED
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] font-mono text-white/40">
                            {timeAgo(updatedAt)}
                          </span>
                        </div>
                        <h3
                          className={`text-base font-display ${
                            isSelected ? "text-lg font-semibold text-white" : "text-white/80"
                          }`}
                        >
                          {incident.source.error_type}: {incident.source.error_message}
                        </h3>
                        <p className="text-xs text-white/40 mt-1 font-mono">
                          {incident.source.source_file}
                          {incident.source.path ? ` (${incident.source.path})` : ""}
                        </p>
                        {isSelected && incident.source.source_file && (
                          <div className="flex items-center gap-2 text-white/50 text-sm font-mono bg-black/50 p-3 rounded-lg border border-white/[0.08] mt-4">
                            <span className="material-symbols-outlined text-base">description</span>
                            {incident.source.source_file}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ---- Pipeline ---------------------------------------- */}
            <div className="bg-[#0A0A0B] rounded-3xl p-8 border border-white/[0.08]">
              <h3 className="text-xs font-display uppercase tracking-widest text-white/50 mb-8">
                Autonomous Resolution Pipeline
              </h3>
              <div className="flex justify-between relative">
                {/* connecting line */}
                <div className="absolute top-4 left-0 w-full h-px bg-white/[0.08] z-0" />

                {PIPELINE_STAGES.map((stage, idx) => {
                  const isBefore = currentStageIdx >= 0 && idx < currentStageIdx;
                  const isCurrent = currentStageIdx >= 0 && idx === currentStageIdx;
                  const isAfter = currentStageIdx < 0 || idx > currentStageIdx;

                  return (
                    <div
                      key={stage.key}
                      className={`relative z-10 flex flex-col items-center gap-3 ${
                        isAfter && !isCurrent ? "opacity-30" : ""
                      }`}
                    >
                      {isCurrent ? (
                        <div className="relative">
                          <div
                            className="absolute inset-0 rounded-full blur-lg animate-pulse"
                            style={{
                              background: `${stage.color}66`,
                            }}
                          />
                          <div
                            className="w-8 h-8 rounded-full flex items-center justify-center text-white relative z-20"
                            style={{ background: stage.color }}
                          >
                            <span
                              className="material-symbols-outlined text-lg animate-spin"
                              style={{ animationDuration: "3s" }}
                            >
                              sync
                            </span>
                          </div>
                        </div>
                      ) : isBefore ? (
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-black shadow-lg"
                          style={{ background: stage.color }}
                        >
                          <span className="material-symbols-outlined text-lg">check</span>
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-white/50">
                          <span className="text-sm">{stage.icon}</span>
                        </div>
                      )}
                      <span
                        className="text-[9px] font-display uppercase font-bold"
                        style={{ color: isBefore || isCurrent ? stage.color : undefined }}
                      >
                        {stage.label}
                      </span>
                      <span className="text-[8px] text-white/30">{stage.sponsor}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ---- Diagnosis & Diff -------------------------------- */}
            <div className="grid grid-cols-2 gap-6">
              {/* Diagnosis */}
              <div className="bg-[#0A0A0B] rounded-2xl p-6 border border-white/[0.08]">
                <div className="flex justify-between items-center mb-6">
                  <h4 className="text-xs font-display uppercase tracking-widest text-white/50">
                    Autonomous Diagnosis
                  </h4>
                  {selectedIncident?.diagnosis.confidence != null && (
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-[#10B981]">
                        {Math.round((selectedIncident.diagnosis.confidence ?? 0) * 100)}%
                        CONFIDENCE
                      </span>
                      <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#10B981] rounded-full"
                          style={{
                            width: `${Math.round((selectedIncident?.diagnosis.confidence ?? 0) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
                {selectedIncident ? (
                  <div className="space-y-4">
                    <div>
                      <p className="text-[10px] font-display uppercase text-white/30 mb-1">
                        Root Cause
                      </p>
                      <p className="text-sm leading-relaxed">
                        {selectedIncident.diagnosis.root_cause ?? "Pending diagnosis..."}
                      </p>
                    </div>
                    {selectedIncident.diagnosis.suggested_fix && (
                      <div>
                        <p className="text-[10px] font-display uppercase text-white/30 mb-1">
                          Suggested Fix
                        </p>
                        <p className="text-sm leading-relaxed text-[#10B981] font-medium">
                          {selectedIncident.diagnosis.suggested_fix}
                        </p>
                      </div>
                    )}
                    {selectedIncident.diagnosis.affected_components &&
                      selectedIncident.diagnosis.affected_components.length > 0 && (
                        <div>
                          <p className="text-[10px] font-display uppercase text-white/30 mb-1">
                            Affected Components
                          </p>
                          <p className="text-sm font-mono text-white/50">
                            {selectedIncident.diagnosis.affected_components.join(" → ")}
                          </p>
                        </div>
                      )}
                    {selectedIncident.diagnosis.severity_reasoning && (
                      <div>
                        <p className="text-[10px] font-display uppercase text-white/30 mb-1">
                          Severity Reasoning
                        </p>
                        <p className="text-sm text-white/50">
                          {selectedIncident.diagnosis.severity_reasoning}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-white/30">Select an incident to view diagnosis.</p>
                )}
              </div>

              {/* Diff */}
              <div className="bg-[#121214] rounded-2xl border border-white/[0.08] overflow-hidden">
                <div className="bg-[#0A0A0B] px-4 py-2 border-b border-white/[0.08] flex justify-between items-center">
                  <span className="text-[10px] font-mono text-white/50">
                    {selectedIncident
                      ? `diff: ${selectedIncident.fix.files_changed?.[0] ?? "patch"}`
                      : "diff: --"}
                  </span>
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-[#FF4B66]/40" />
                    <div className="w-2 h-2 rounded-full bg-[#10B981]/40" />
                  </div>
                </div>
                <div className="p-4 font-mono text-[11px] leading-loose overflow-x-auto max-h-[300px] overflow-y-auto">
                  {diffLines.length > 0 ? (
                    diffLines.map((line, i) => (
                      <div
                        key={`${i}-${line.text}`}
                        className={
                          line.kind === "add"
                            ? "text-[#10B981]"
                            : line.kind === "remove"
                              ? "text-[#FF4B66]"
                              : line.kind === "header"
                                ? "text-[#634BFF]"
                                : "text-white/30"
                        }
                      >
                        {line.text || " "}
                      </div>
                    ))
                  ) : (
                    <p className="text-white/30">
                      {selectedIncident
                        ? "No diff preview available yet."
                        : "Select an incident to view the diff."}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* RIGHT COLUMN                                               */}
          {/* ======================================================== */}
          <div className="col-span-12 lg:col-span-5 space-y-8">
            {/* ---- Sponsor chips ----------------------------------- */}
            <div className="bg-[#0A0A0B] rounded-3xl p-6 border border-white/[0.08]">
              <h3 className="text-[10px] font-display uppercase tracking-[0.2em] text-white/30 mb-6">
                Active Infrastructure Graph
              </h3>
              <div className="flex flex-wrap gap-2">
                {SPONSORS.map((s) => (
                  <div
                    key={s.name}
                    className="px-4 py-2 rounded-full text-[10px] font-bold tracking-widest border"
                    style={{
                      color: s.color,
                      backgroundColor: `${s.color}15`,
                      borderColor: `${s.color}4D`,
                    }}
                  >
                    {s.name.toUpperCase()}
                  </div>
                ))}
              </div>
            </div>

            {/* ---- Bland AI Call Card ------------------------------ */}
            {awaitingIncident && (
              <div className="relative" style={{ boxShadow: "0 0 50px -10px rgba(99,75,255,0.3)" }}>
                <div className="relative bg-[#121214]/90 backdrop-blur-xl rounded-3xl p-8 border border-[#634BFF]/40 shadow-2xl overflow-hidden">
                  <div className="absolute -top-12 -right-12 w-32 h-32 bg-[#634BFF]/10 rounded-full blur-2xl" />
                  <div className="flex items-center gap-6">
                    <div className="relative">
                      <div className="absolute inset-0 bg-[#634BFF] rounded-full animate-ping opacity-20" />
                      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#634BFF] to-[#4D39E6] flex items-center justify-center shadow-lg shadow-[#634BFF]/40 relative z-10">
                        <span className="material-symbols-outlined text-3xl text-white">call</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-display uppercase font-bold text-[#634BFF] tracking-widest">
                          Bland AI Escalation
                        </span>
                        <span className="w-1 h-1 rounded-full bg-[#634BFF]/40" />
                        <span className="text-[10px] font-display uppercase text-white/50">
                          Live Call
                        </span>
                      </div>
                      <h2 className="text-xl font-display font-bold text-white">
                        Calling On-Call Engineer
                      </h2>
                      <p className="text-sm text-white/50 mt-1">
                        {shortId(awaitingIncident.incident_id)}:{" "}
                        {awaitingIncident.source.error_type} on{" "}
                        {awaitingIncident.source.path ?? awaitingIncident.source.source_file}{" "}
                        &mdash; {awaitingIncident.severity} severity, requesting deployment
                        approval...
                      </p>
                    </div>
                  </div>
                  <div className="mt-6 flex gap-3">
                    <button
                      onClick={() => {
                        setSelectedIncidentId(awaitingIncident.incident_id);
                        void handleApprove();
                      }}
                      disabled={isSubmitting}
                      className="flex-1 py-3 bg-[#10B981]/10 border border-[#10B981]/30 rounded-xl text-[#10B981] text-xs font-bold uppercase tracking-widest hover:bg-[#10B981]/20 transition-all disabled:opacity-50"
                    >
                      {isSubmitting ? "Submitting..." : "Approve Deploy"}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedIncidentId(awaitingIncident.incident_id);
                        void handleReject();
                      }}
                      disabled={isSubmitting}
                      className="px-6 py-3 bg-[#FF4B66]/10 border border-[#FF4B66]/30 rounded-xl text-[#FF4B66] text-xs font-bold uppercase tracking-widest hover:bg-[#FF4B66]/20 transition-all disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                  {approvalError && (
                    <p className="mt-3 text-xs text-[#FF4B66]">{approvalError}</p>
                  )}
                </div>
              </div>
            )}

            {/* ---- Agent Logs -------------------------------------- */}
            <div className="bg-[#121214] rounded-3xl border border-white/[0.08] overflow-hidden h-[400px] flex flex-col">
              <div className="bg-[#0A0A0B] px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
                <h4 className="text-xs font-display uppercase tracking-widest text-white/50">
                  System Activity Log
                </h4>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      streamState === "live" ? "bg-[#10B981]" : "bg-[#FF4B66]"
                    }`}
                  />
                  <span className="text-[10px] font-mono text-white/50">
                    {streamState === "live" ? "SSE STREAMING" : streamState.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="flex-1 p-4 font-mono text-[11px] leading-relaxed text-white/50 overflow-y-auto space-y-0.5">
                {allTimelineEvents.length === 0 ? (
                  <p className="text-white/30 text-center py-8">
                    No timeline events yet. Trigger a bug to see activity.
                  </p>
                ) : (
                  allTimelineEvents.map((evt, i) => {
                    const sponsorInfo = SPONSORS.find(
                      (s) => s.name.toLowerCase() === (evt.sponsor ?? evt.actor ?? "").toLowerCase(),
                    );
                    const color = sponsorInfo?.color ?? "#A9ABB3";
                    const statusColor =
                      evt.status === "resolved" ? "#10B981"
                        : evt.status === "failed" ? "#FF4B66"
                          : evt.status === "awaiting_approval" ? "#6366F1"
                            : undefined;
                    return (
                      <div
                        key={`${evt.at_ms}-${i}`}
                        className="flex items-start gap-2 py-1.5 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] px-2 rounded transition-colors"
                      >
                        <span className="shrink-0 w-1.5 h-1.5 rounded-full mt-1.5" style={{ background: color }} />
                        <span className="shrink-0 text-white/30 w-[70px]">{formatTime(evt.at_ms)}</span>
                        <span className="shrink-0 font-bold w-[130px] truncate" style={{ color }}>{evt.actor ?? evt.sponsor ?? "System"}</span>
                        <span style={{ color: statusColor }} className="flex-1">{evt.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* ---- Overmind Traces --------------------------------- */}
            <div className="bg-[#0A0A0B] rounded-2xl p-6 border border-white/[0.08]">
              <h4 className="text-xs font-display uppercase tracking-widest text-white/50 mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#A855F7]" />
                Overmind Traces
              </h4>
              <div className="space-y-2">
                {incidents.length === 0 ? (
                  <p className="text-[11px] font-mono text-white/30">No traces yet.</p>
                ) : (
                  incidents.map((incident, i) => {
                    const obs = incident.observability as Record<string, unknown> | undefined;
                    const traceId = obs?.overmind_trace_id as string | undefined;
                    const timelineLen = incident.timeline?.length ?? 0;
                    const durationMs = incident.resolution_time_ms
                      ?? (incident.updated_at_ms - incident.created_at_ms);
                    const durationSec = Math.round(durationMs / 1000);
                    const sevColor = SEVERITY_COLORS[incident.severity] ?? "#A9ABB3";
                    const statusIcon =
                      incident.status === "resolved" ? "check_circle"
                        : incident.status === "failed" ? "error"
                          : incident.status === "awaiting_approval" ? "hourglass_top"
                            : "sync";
                    const statusColor =
                      incident.status === "resolved" ? "#10B981"
                        : incident.status === "failed" ? "#FF4B66"
                          : incident.status === "awaiting_approval" ? "#6366F1"
                            : "#FDE68A";
                    const isLast = i === incidents.length - 1;

                    return (
                      <div
                        key={incident.incident_id}
                        className={`flex items-center gap-3 text-[11px] font-mono py-2 ${
                          !isLast ? "border-b border-white/[0.06]" : ""
                        }`}
                      >
                        <span className="material-symbols-outlined text-sm" style={{ color: statusColor }}>{statusIcon}</span>
                        <span style={{ color: "#A855F7" }} className="font-bold shrink-0">
                          {shortId(incident.incident_id)}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase" style={{ color: sevColor, backgroundColor: `${sevColor}15` }}>
                          {incident.severity}
                        </span>
                        <div className="flex-1" />
                        <span className="text-white/30">{timelineLen} events</span>
                        <span className="text-white/50">{durationSec > 0 ? `${durationSec}s` : "<1s"}</span>
                        <span className="text-white/20">{incident.status}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* ---- Footer ----------------------------------------- */}
            <div className="bg-[#0A0A0B] rounded-2xl p-6 border border-white/[0.08]">
              <div className="flex items-center justify-between opacity-50">
                <span className="text-[10px] font-display uppercase tracking-widest">
                  DeepOps v1.0 &bull; Deep Agents Hackathon 2026
                </span>
                <div className="flex gap-4">
                  <span className="material-symbols-outlined text-base cursor-pointer hover:text-white">
                    support
                  </span>
                  <span className="material-symbols-outlined text-base cursor-pointer hover:text-white">
                    help_center
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Keyframe for pulse-high animation */}
      <style>{`
        @keyframes pulse-high {
          0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 20px rgba(255, 75, 102, 0.4); }
          50% { opacity: 0.9; transform: scale(0.98); box-shadow: 0 0 40px rgba(255, 75, 102, 0.6); }
        }
      `}</style>
    </>
  );
}
