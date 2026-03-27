"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useBackendHealth } from "../dashboard/hooks/useBackendHealth";

type IntegrationStatus = "active" | "fallback" | "partial" | "halted";

type SettingsOverview = {
  system: {
    service_name: string;
    environment: string;
    system_id: string;
    terminal_version: string;
    maintenance_mode: boolean;
    backend: string;
    store: string;
    allow_in_memory_store: boolean;
  };
  webhook: {
    url: string;
    label: string;
    note: string;
  };
  integrations: Array<{
    name: string;
    status: IntegrationStatus;
    summary: string;
    action_label: string;
    color: string;
    details: string[];
  }>;
  runtime: {
    generated_at_ms: number;
    api_host: string;
    api_port: number;
    realtime_heartbeat_seconds: number;
    demo_app_base_url: string;
  };
};

const topLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard", label: "Incidents" },
  { href: "/metrics", label: "Metrics" },
] as const;

const sideLinks: Array<{
  href: string;
  label: string;
  active?: boolean;
}> = [
  { href: "/dashboard", label: "Incidents" },
  { href: "/metrics", label: "Metrics" },
  { href: "/dashboard", label: "Logs" },
  { href: "/settings", label: "Settings", active: true },
];

function formatTimestamp(timestampMs: number | null) {
  if (!timestampMs) {
    return "Pending";
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(timestampMs);
}

function statusTone(status: IntegrationStatus) {
  if (status === "active") {
    return {
      dot: "bg-[#00DAF3] shadow-[0_0_8px_rgba(0,218,243,0.45)]",
      text: "text-[#00DAF3]",
      label: "Active",
    };
  }

  if (status === "fallback") {
    return {
      dot: "bg-[#634BFF] shadow-[0_0_8px_rgba(99,75,255,0.45)]",
      text: "text-[#634BFF]",
      label: "Fallback",
    };
  }

  if (status === "partial") {
    return {
      dot: "bg-[#FFB4AB] shadow-[0_0_8px_rgba(255,180,171,0.45)]",
      text: "text-[#FFB4AB]",
      label: "Partial",
    };
  }

  return {
    dot: "bg-[#EB5424] shadow-[0_0_8px_rgba(235,84,36,0.45)]",
    text: "text-[#EB5424]",
    label: "Halted",
  };
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { status: backendStatus, lastCheckedAt } = useBackendHealth();

  const loadSettings = async (background = false) => {
    if (background) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const response = await fetch("/api/settings/overview", {
        cache: "no-store",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }

      const payload = (await response.json()) as SettingsOverview;
      setData(payload);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to load settings.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadSettings();
  }, []);

  const handleCopy = async () => {
    if (!data?.webhook.url) {
      return;
    }

    try {
      await navigator.clipboard.writeText(data.webhook.url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <main className="min-h-screen bg-black font-body-ui text-[#E1E2EB] antialiased">
      <header className="fixed top-0 left-0 z-50 flex w-full items-center justify-between bg-[#0B0E14] px-6 py-4">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="font-display text-2xl font-black uppercase tracking-[0.16em] text-[#634BFF]"
          >
            DeepOps Mission Control
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            {topLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="font-display font-bold tracking-tight text-[#E1E2EB] opacity-70 transition-colors duration-200 hover:text-[#634BFF]"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#272A31] px-3 py-1.5">
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-white/55">
              Maintenance Mode
            </span>
            <div className="relative inline-flex h-5 w-10 items-center rounded-full bg-[#32353C]">
              <span
                className={`absolute left-0.5 inline-block h-4 w-4 rounded-full transition-transform ${
                  data?.system.maintenance_mode ? "translate-x-5 bg-[#634BFF]" : "translate-x-0 bg-[#928EA2]"
                }`}
              />
            </div>
          </div>
          <div className="flex items-center gap-4 text-white/58">
            <span className="font-mono text-xs uppercase">NT</span>
            <span className="font-mono text-xs uppercase">SG</span>
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#634BFF]/20 bg-[#121212] font-display text-xs font-bold uppercase text-white">
              DO
            </span>
          </div>
        </div>
      </header>

      <aside className="fixed top-0 left-0 z-40 hidden h-screen w-64 flex-col border-r border-[#474556]/15 bg-[#10131A] pt-24 shadow-[40px_0_40px_rgba(0,0,0,0.06)] md:flex">
        <div className="mb-8 px-6">
          <h2 className="font-display text-lg font-bold text-[#634BFF]">DeepOps</h2>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/38">
            {data?.system.terminal_version ?? "v0.1.0"}
          </p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {sideLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className={`flex items-center gap-3 px-6 py-3 text-sm font-medium transition-all ${
                link.active
                  ? "rounded-r-lg border-l-4 border-[#634BFF] bg-[#191C22] text-[#634BFF]"
                  : "text-white/60 hover:bg-[#191C22] hover:text-[#E1E2EB]"
              }`}
            >
              <span className="font-mono text-[10px] uppercase tracking-[0.2em]">
                {link.label.slice(0, 2)}
              </span>
              <span>{link.label}</span>
            </Link>
          ))}
        </nav>
        <div className="p-6">
          <button
            type="button"
            onClick={() => {
              void loadSettings(true);
            }}
            className="w-full rounded-xl bg-[#634BFF] py-3 font-display text-sm font-bold text-white transition-transform active:scale-95"
          >
            {refreshing ? "Refreshing…" : "Refresh Settings"}
          </button>
        </div>
      </aside>

      <main className="min-h-screen px-10 pt-24 pb-20 md:ml-64">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 flex items-end justify-between">
            <div>
              <h1 className="mb-2 font-display text-4xl font-black tracking-tight text-white">
                System Configuration
              </h1>
              <p className="max-w-xl text-white/62">
                Manage global endpoints, identity gates, and sponsor integration
                health from the same DeepOps control surface.
              </p>
            </div>
            <div className="text-right">
              <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">
                SYSTEM_ID
              </div>
              <div className="font-mono text-xs text-[#00DAF3]">
                {data?.system.system_id ?? "loading"}
              </div>
            </div>
          </div>

          <section className="mb-8">
            <div className="group kinetic-gradient relative overflow-hidden rounded-xl border border-white/8 bg-[#191C22] p-8">
              <div className="absolute -top-10 -right-10 h-64 w-64 rounded-full bg-[#634BFF]/10 blur-3xl transition-all duration-700 group-hover:bg-[#634BFF]/15" />
              <div className="relative z-10 flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="font-display text-xl text-[#634BFF]">⛓</span>
                    <h3 className="font-display text-lg font-bold text-white">
                      Global Webhook URL
                    </h3>
                  </div>
                  <p className="mb-4 text-sm text-white/58">
                    {data?.webhook.note ??
                      "Primary callback path for sponsor workflows and incident escalations."}
                  </p>
                  <div className="flex items-center gap-4 rounded-lg border border-white/8 bg-[#0B0E14] p-4 shadow-inner">
                    <code className="flex-1 break-all font-mono text-sm text-[#634BFF]">
                      {data?.webhook.url ?? "Loading webhook URL…"}
                    </code>
                    <button
                      type="button"
                      onClick={handleCopy}
                      className="rounded-lg p-2 text-white/55 transition-colors hover:bg-[#272A31] hover:text-white"
                    >
                      {copied ? "OK" : "CP"}
                    </button>
                  </div>
                </div>
                <div className="flex w-full flex-col gap-3 md:w-auto">
                  <button
                    type="button"
                    onClick={() => {
                      void loadSettings(true);
                    }}
                    className="flex items-center justify-center gap-2 rounded-xl bg-[#634BFF] px-6 py-3 font-display text-sm font-bold text-white shadow-lg shadow-[#634BFF]/20 transition-all hover:brightness-110"
                  >
                    {refreshing ? "Refreshing…" : "Refresh Status"}
                  </button>
                  <span className="text-center font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">
                    Updated {formatTimestamp(data?.runtime.generated_at_ms ?? null)}
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-6 flex items-center justify-between">
              <h3 className="font-display text-xl font-bold text-white">
                Infrastructure Partners
              </h3>
              <div className="mx-6 h-px flex-1 bg-gradient-to-r from-white/12 to-transparent" />
              <span className="rounded bg-[#00DAF3]/10 px-2 py-0.5 font-mono text-[10px] uppercase text-[#00DAF3]">
                Live Sync
              </span>
            </div>

            {loading && !data ? (
              <div className="rounded-xl border border-white/8 bg-[#191C22] p-6 text-sm text-white/55">
                Loading settings overview…
              </div>
            ) : error ? (
              <div className="rounded-xl border border-[#EB5424]/30 bg-[#191C22] p-6 text-sm text-[#FFB4AB]">
                {error}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                {data?.integrations.map((integration) => {
                  const tone = statusTone(integration.status);
                  return (
                    <div
                      key={integration.name}
                      className="group rounded-xl border border-white/8 bg-[#191C22] p-5 transition-all hover:border-[#634BFF]/30"
                    >
                      <div className="mb-6 flex items-start justify-between">
                        <div
                          className="flex h-10 w-10 items-center justify-center rounded-lg"
                          style={{ backgroundColor: `${integration.color}1A` }}
                        >
                          <span
                            className="font-display text-sm font-bold"
                            style={{ color: integration.color }}
                          >
                            {integration.name.slice(0, 2).toUpperCase()}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 rounded-full border border-white/6 bg-[#0B0E14] px-2 py-1">
                          <div className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
                          <span className={`font-mono text-[10px] uppercase ${tone.text}`}>
                            {tone.label}
                          </span>
                        </div>
                      </div>

                      <h4 className="mb-1 font-display font-bold text-white">
                        {integration.name}
                      </h4>
                      <p className="mb-4 text-xs leading-relaxed text-white/55">
                        {integration.summary}
                      </p>

                      <div className="space-y-1 rounded-lg bg-[#0B0E14] p-3">
                        {integration.details.slice(0, 2).map((detail) => (
                          <div
                            key={detail}
                            className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/42"
                          >
                            {detail}
                          </div>
                        ))}
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-white/6 pt-4">
                        <button
                          type="button"
                          onClick={() => {
                            void loadSettings(true);
                          }}
                          className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-white/55 transition-colors hover:text-[#634BFF]"
                        >
                          {integration.action_label}
                        </button>
                        <span className="font-display text-sm text-white/38 transition-transform group-hover:translate-x-1">
                          →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="fixed right-0 bottom-0 left-0 z-40 flex items-center justify-between border-t border-white/6 bg-[#0B0E14] px-6 py-3 md:left-64 md:px-10">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/35">
              Last Update:
            </span>
            <span className="font-mono text-xs text-[#00DAF3]">
              {formatTimestamp(data?.runtime.generated_at_ms ?? null)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/35">
              Runtime:
            </span>
            <div className="flex items-center gap-1">
              <span className="font-mono text-xs text-white">
                {data?.runtime.api_host ?? "127.0.0.1"}:{data?.runtime.api_port ?? 8000}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={`h-2 w-2 rounded-full ${
                backendStatus === "live"
                  ? "bg-[#00DAF3] animate-pulse"
                  : backendStatus === "offline"
                    ? "bg-[#EB5424]"
                    : "bg-[#FFB4AB]"
              }`}
            />
            <span
              className={`font-mono text-[10px] uppercase tracking-[0.16em] ${
                backendStatus === "live"
                  ? "text-[#00DAF3]"
                  : backendStatus === "offline"
                    ? "text-[#EB5424]"
                    : "text-[#FFB4AB]"
              }`}
            >
              {backendStatus === "live" ? "All Systems Operational" : backendStatus.toUpperCase()}
            </span>
          </div>
          <div className="h-4 w-px bg-white/10" />
          <span className="font-mono text-[9px] text-white/26">
            © DEEPOPS CORE ARCHITECTURE
          </span>
        </div>
      </footer>
    </main>
  );
}
