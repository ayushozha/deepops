import Link from "next/link";

const sponsorTools = [
  "Airbyte",
  "Aerospike",
  "Macroscope",
  "Kiro",
  "Auth0",
  "Bland AI",
  "TrueFoundry",
  "Overmind",
];

const architectureSteps = [
  "Ingest runtime signals from the backend and normalize incident state.",
  "Synthesize diagnosis, patch candidates, and approval context with deep agents.",
  "Route high-risk fixes through human approval before deployment.",
  "Keep the system self-healing by combining streams, retries, and reconciliation.",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(0,212,255,0.18),_transparent_36%),linear-gradient(180deg,#08111f_0%,#07101a_48%,#050b12_100%)] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-6 sm:px-10 lg:px-12">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/15 pb-5">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.35em] text-cyan-300/80">
              DeepOps
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
              Self-healing codebases powered by deep agents
            </h1>
          </div>
          <Link
            href="https://github.com/ayushozha/deepops"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-cyan-400/40 bg-white/5 px-4 py-2 font-mono text-sm text-cyan-100 transition hover:border-cyan-300 hover:bg-white/10"
          >
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_20px_rgba(0,212,255,0.8)]" />
            GitHub
          </Link>
        </header>

        <section className="grid flex-1 gap-6 py-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-stretch">
          <div className="flex flex-col justify-between rounded-[2rem] border border-white/15 bg-white/[0.04] p-8 shadow-[0_0_0_1px_rgba(0,212,255,0.06),0_30px_80px_rgba(0,0,0,0.35)] backdrop-blur">
            <div className="space-y-6">
              <div className="inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1 font-mono text-xs uppercase tracking-[0.3em] text-cyan-100">
                pitch
              </div>
              <div className="max-w-3xl space-y-4">
                <p className="font-mono text-sm uppercase tracking-[0.3em] text-white/55">
                  Autonomous remediation for production-grade systems
                </p>
                <p className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                  Replace incident panic with an agentic repair loop.
                </p>
                <p className="max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
                  DeepOps keeps the repair path visible: diagnose the failure,
                  draft the patch, present the diff, and route risk through a
                  human approval gate when the fix needs it.
                </p>
              </div>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                  architecture
                </p>
                <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
                  {architectureSteps.map((step) => (
                    <li key={step} className="flex gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300" />
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/8 p-5">
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                  dashboard
                </p>
                <p className="mt-4 text-sm leading-6 text-slate-300">
                  Explore incident history, diff previews, and approval status in
                  a single operator view at{" "}
                  <Link href="/dashboard" className="text-cyan-200 underline-offset-4 hover:underline">
                    /dashboard
                  </Link>
                  .
                </p>
              </div>
            </div>
          </div>

          <aside className="flex flex-col gap-6 rounded-[2rem] border border-white/15 bg-slate-950/70 p-8">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-cyan-200/70">
                sponsor tools
              </p>
              <h2 className="mt-3 text-2xl font-semibold text-white">
                Built around the stack that keeps the loop moving.
              </h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {sponsorTools.map((tool) => (
                <div
                  key={tool}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-200"
                >
                  {tool}
                </div>
              ))}
            </div>
            <div className="mt-auto rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(0,212,255,0.15),rgba(0,212,255,0.04))] p-5">
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-100/70">
                call to action
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Open the operational dashboard to inspect incident flow,
                confirm a patch, and keep the backend observable.
              </p>
              <Link
                href="/dashboard"
                className="mt-5 inline-flex items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-300/10 px-5 py-3 font-mono text-sm text-cyan-100 transition hover:bg-cyan-300/15"
              >
                Enter dashboard
              </Link>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
