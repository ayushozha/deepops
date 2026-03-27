import Link from "next/link";

import { Pill } from "./dashboard-ui";

const statusTone = {
  LIVE: "green",
  DEGRADED: "orange",
  OFFLINE: "red",
} as const;

export function DashboardHeader({
  connectionState,
}: {
  connectionState: "LIVE" | "DEGRADED" | "OFFLINE";
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/15 px-5 py-4 sm:px-6">
      <div>
        <p className="font-mono text-[0.72rem] uppercase tracking-[0.36em] text-cyan-200/70">
          DeepOps
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">
          Operational dashboard
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <Pill tone={statusTone[connectionState]} className="text-[0.66rem]">
          ● {connectionState}
        </Pill>
        <Link
          href="https://github.com/ayushozha/deepops"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 font-mono text-xs uppercase tracking-[0.24em] text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
        >
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          GitHub
        </Link>
      </div>
    </header>
  );
}

