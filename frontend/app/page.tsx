import Link from "next/link";

const pipelineStages = [
  {
    sponsor: "Airbyte",
    stage: "Ingest",
    color: "#634BFF",
    summary: "Normalizes runtime failures and app signals into a canonical incident input.",
  },
  {
    sponsor: "Aerospike",
    stage: "Store",
    color: "#C4302B",
    summary: "Persists the live incident record so every agent and operator sees the same truth.",
  },
  {
    sponsor: "Macroscope",
    stage: "Diagnose",
    color: "#00B4D8",
    summary: "Builds root-cause context from traces, symptoms, code signals, and runtime evidence.",
  },
  {
    sponsor: "Kiro",
    stage: "Fix",
    color: "#FF9900",
    summary: "Produces constrained fix plans, diff previews, test intent, and execution artifacts.",
  },
  {
    sponsor: "Auth0",
    stage: "Gate",
    color: "#EB5424",
    summary: "Handles approval, rejection, and human suggestion loops before risky changes go live.",
  },
  {
    sponsor: "Bland AI",
    stage: "Escalate",
    color: "#6366F1",
    summary: "Calls the human when blast radius, user cost, or revenue risk crosses the threshold.",
  },
  {
    sponsor: "TrueFoundry",
    stage: "Deploy",
    color: "#10B981",
    summary: "Rolls out the selected fix and reports deployment truth back into the incident record.",
  },
  {
    sponsor: "Overmind",
    stage: "Optimize",
    color: "#A855F7",
    summary: "Captures traces and optimization signals so the repair loop gets better over time.",
  },
] as const;

const demoFlows = [
  {
    route: "/calculate/0",
    severity: "medium",
    title: "Autonomous self-heal",
    description:
      "The agent detects the regression, diagnoses root cause, drafts a fix, deploys it, and closes the loop without stopping the operator.",
    decisions: [
      "No human gate when the incident stays within the safe policy envelope.",
      "The dashboard still shows live diagnosis, diff preview, and deployment progress.",
      "Best demo path for showing the full machine-speed remediation loop.",
    ],
  },
  {
    route: "/user/unknown",
    severity: "high",
    title: "Approval and steering",
    description:
      "The system reaches gating and waits for approve, reject, or suggest so the operator can steer the outcome before deploy.",
    decisions: [
      "Approve or reject the proposed plan, fix, and merge path.",
      "Suggest constraints or alternate steps and let the agent re-plan around them.",
      "This is the human-in-the-loop path reflected in the dashboard controls.",
    ],
  },
  {
    route: "/search",
    severity: "critical",
    title: "Phone escalation",
    description:
      "When the issue has major user or financial impact, Bland AI calls the human and turns voice guidance into an actionable hotfix plan.",
    decisions: [
      "If the human is away from the computer, they can still direct the fix over the call.",
      "If they can operate live, the agent follows the guidance and keeps the backend synchronized.",
      "This is the highest-signal hackathon moment because it proves escalation, approval, and execution together.",
    ],
  },
] as const;

const lifecycleStates = [
  "detected",
  "stored",
  "diagnosing",
  "fixing",
  "gating",
  "awaiting_approval",
  "deploying",
  "resolved",
] as const;

const dashboardCapabilities = [
  "Live incident stream over SSE with polling fallback.",
  "Canonical incident detail, severity, and state transitions.",
  "Diff preview, plan status, and approval controls in one operator surface.",
  "Deployment and webhook feedback reflected back into the same record.",
] as const;

const apiSurfaces = [
  "GET /api/incidents",
  "GET /api/incidents/stream",
  "POST /api/agent/run-once",
  "POST /api/approval/{incident_id}/decision",
  "POST /api/webhooks/bland",
  "POST /api/webhooks/truefoundry",
] as const;

const schemaPreview = [
  "incident_id: inc_search_critical",
  "status: awaiting_approval",
  "severity: critical",
  "source.route: /search",
  "diagnosis.summary: cache stampede after null query fanout",
  "fix.status: complete",
  "approval.status: pending",
  "deployment.status: not_started",
  "timeline: detect -> diagnose -> fix -> gate -> escalate",
] as const;

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-black text-white">
      <div className="scanline-overlay" />

      <header className="fixed inset-x-0 top-0 z-20 border-b border-white/10 bg-black/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-[1500px] items-center justify-between px-5 sm:px-8 lg:px-10">
          <div className="flex items-center gap-4">
            <div className="font-display text-xl font-black uppercase tracking-[0.16em] text-[#634BFF]">
              DeepOps
            </div>
            <div className="hidden font-label-ui text-[11px] uppercase tracking-[0.28em] text-white/45 sm:block">
              Mission Control
            </div>
          </div>

          <nav className="hidden items-center gap-8 font-label-ui text-[11px] uppercase tracking-[0.26em] text-white/60 md:flex">
            <a href="#pipeline" className="transition hover:text-white">
              Pipeline
            </a>
            <a href="#flows" className="transition hover:text-white">
              Demo Flows
            </a>
            <a href="#contract" className="transition hover:text-white">
              Incident Record
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="hidden rounded-sm border border-white/12 px-4 py-2 font-label-ui text-[11px] uppercase tracking-[0.24em] text-white/80 transition hover:border-white/30 hover:text-white sm:inline-flex"
            >
              Open Dashboard
            </Link>
            <a
              href="#flows"
              className="trigger-glow inline-flex rounded-sm bg-[linear-gradient(135deg,#634BFF_0%,#8B5CF6_100%)] px-4 py-2 font-label-ui text-[11px] uppercase tracking-[0.24em] text-white transition hover:brightness-110"
            >
              Trigger Demo
            </a>
          </div>
        </div>
      </header>

      <section className="relative min-h-[100svh] border-b border-white/8 px-5 pt-24 pb-12 sm:px-8 lg:px-10">
        <div className="mx-auto grid min-h-[calc(100svh-6rem)] max-w-[1500px] items-end gap-14 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="relative flex flex-col justify-between py-8">
            <div className="absolute inset-y-0 right-[-8%] hidden w-[38rem] bg-[radial-gradient(circle_at_center,rgba(99,75,255,0.20),transparent_62%)] lg:block" />

            <div className="relative z-10 max-w-4xl">
              <div className="mb-8 inline-flex items-center gap-3 rounded-full border border-[#634BFF]/30 bg-[#634BFF]/8 px-4 py-2">
                <span className="h-2 w-2 rounded-full bg-[#10B981]" />
                <span className="font-label-ui text-[11px] uppercase tracking-[0.28em] text-[#D9D4FF]">
                  Live incident loop active
                </span>
              </div>

              <div className="mb-5 font-label-ui text-[12px] uppercase tracking-[0.4em] text-white/40">
                Autonomous incident repair for live production systems
              </div>

              <h1 className="font-display max-w-5xl text-5xl font-black uppercase leading-[0.92] tracking-[-0.04em] text-white sm:text-7xl xl:text-[6.3rem]">
                The self-healing control plane for code, approval, escalation,
                and deploy.
              </h1>

              <p className="mt-8 max-w-2xl text-lg leading-8 text-white/70 sm:text-xl">
                DeepOps watches a live app, detects failures in real time,
                understands the codebase, writes the fix, deploys it, and only
                calls the human when the blast radius demands it.
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  href="/dashboard"
                  className="trigger-glow inline-flex items-center rounded-sm bg-[linear-gradient(135deg,#634BFF_0%,#8B5CF6_100%)] px-7 py-4 font-display text-base font-bold uppercase tracking-[0.08em] text-white transition hover:brightness-110"
                >
                  Open Mission Control
                </Link>
                <a
                  href="#contract"
                  className="inline-flex items-center rounded-sm border border-white/12 px-7 py-4 font-display text-base font-bold uppercase tracking-[0.08em] text-white/80 transition hover:border-white/30 hover:text-white"
                >
                  View Incident Contract
                </a>
              </div>
            </div>

            <div className="relative z-10 mt-14 flex flex-wrap gap-8 font-label-ui text-[11px] uppercase tracking-[0.26em] text-white/55">
              <div>
                <div className="mb-2 text-[#10B981]">Flow A</div>
                <div className="text-white">Autonomous auto-fix</div>
              </div>
              <div>
                <div className="mb-2 text-[#EB5424]">Flow B</div>
                <div className="text-white">Approval and suggestion loop</div>
              </div>
              <div>
                <div className="mb-2 text-[#6366F1]">Flow C</div>
                <div className="text-white">Bland AI voice escalation</div>
              </div>
            </div>
          </div>

          <aside className="glass-panel command-glow relative overflow-hidden rounded-2xl p-6 sm:p-8">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,75,255,0.16),transparent_40%)]" />
            <div className="relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-label-ui text-[11px] uppercase tracking-[0.28em] text-white/45">
                    Operator surface
                  </div>
                  <div className="mt-2 font-display text-2xl font-bold uppercase tracking-tight">
                    One record. One queue. One decision loop.
                  </div>
                </div>
                <div className="rounded-full border border-white/12 px-3 py-1 font-label-ui text-[10px] uppercase tracking-[0.24em] text-[#10B981]">
                  Live
                </div>
              </div>

              <div className="mt-8 space-y-5">
                {dashboardCapabilities.map((capability) => (
                  <div
                    key={capability}
                    className="border-l border-white/12 pl-4 text-sm leading-6 text-white/68"
                  >
                    {capability}
                  </div>
                ))}
              </div>

              <div className="mt-8 rounded-xl border border-white/10 bg-black/55 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-label-ui text-[10px] uppercase tracking-[0.24em] text-white/40">
                      Current mission
                    </div>
                    <div className="mt-2 font-display text-lg font-bold uppercase">
                      Search outage escalation
                    </div>
                  </div>
                  <div className="rounded-full border border-[#6366F1]/35 px-3 py-1 font-label-ui text-[10px] uppercase tracking-[0.22em] text-[#C7CCFF]">
                    Critical
                  </div>
                </div>
                <div className="mt-4 grid gap-3 font-label-ui text-[11px] uppercase tracking-[0.18em] text-white/55">
                  <div className="flex items-center justify-between border-b border-white/8 pb-3">
                    <span>Status</span>
                    <span className="text-white">awaiting_approval</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/8 pb-3">
                    <span>Next action</span>
                    <span className="text-white">Call operator via Bland</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Deploy path</span>
                    <span className="text-white">TrueFoundry callback pending</span>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section id="pipeline" className="border-b border-white/8 px-5 py-24 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[1500px]">
          <div className="mb-14 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="font-label-ui text-[11px] uppercase tracking-[0.34em] text-white/42">
                Sponsor pipeline
              </div>
              <h2 className="mt-4 font-display text-4xl font-black uppercase tracking-[-0.03em] sm:text-5xl">
                Eight stages. One closed-loop incident system.
              </h2>
            </div>
            <p className="max-w-2xl text-base leading-7 text-white/62">
              The landing page has to tell the truth about the system. These
              are the actual roles each sponsor tool plays inside the DeepOps
              remediation loop.
            </p>
          </div>

          <div className="grid gap-px bg-white/8 md:grid-cols-2 xl:grid-cols-4">
            {pipelineStages.map((stage, index) => (
              <div
                key={stage.sponsor}
                className="group relative min-h-64 overflow-hidden bg-black px-7 py-7 transition duration-300 hover:bg-[#05070d]"
              >
                <div
                  className="absolute inset-x-0 top-0 h-px opacity-80"
                  style={{ backgroundColor: stage.color }}
                />
                <div
                  className="absolute inset-0 opacity-0 transition duration-300 group-hover:opacity-100"
                  style={{
                    background: `radial-gradient(circle at top right, ${stage.color}22, transparent 45%)`,
                  }}
                />
                <div className="relative z-10 flex h-full flex-col justify-between">
                  <div className="flex items-start justify-between">
                    <div className="font-label-ui text-[11px] uppercase tracking-[0.22em] text-white/42">
                      {String(index + 1).padStart(2, "0")} / {stage.stage}
                    </div>
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: stage.color }}
                    />
                  </div>
                  <div>
                    <div
                      className="font-display text-3xl font-bold uppercase tracking-tight"
                      style={{ color: stage.color }}
                    >
                      {stage.sponsor}
                    </div>
                    <p className="mt-4 max-w-xs text-sm leading-7 text-white/65">
                      {stage.summary}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="flows" className="border-b border-white/8 px-5 py-24 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[1500px]">
          <div className="mb-14 max-w-3xl">
            <div className="font-label-ui text-[11px] uppercase tracking-[0.34em] text-white/42">
              Live demo paths
            </div>
            <h2 className="mt-4 font-display text-4xl font-black uppercase tracking-[-0.03em] sm:text-5xl">
              Three flows that prove the system is real.
            </h2>
            <p className="mt-5 text-base leading-7 text-white/62">
              The demo is not one synthetic happy path. It is three escalating
              branches: autonomous remediation, human approval, and phone-based
              escalation with executable guidance.
            </p>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            {demoFlows.map((flow) => (
              <div
                key={flow.route}
                className="glass-panel rounded-2xl p-7 transition duration-300 hover:-translate-y-1 hover:border-white/18"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-label-ui text-[10px] uppercase tracking-[0.24em] text-white/38">
                      Failure route
                    </div>
                    <div className="mt-2 font-display text-2xl font-bold uppercase tracking-tight">
                      {flow.title}
                    </div>
                  </div>
                  <div className="rounded-full border border-white/12 px-3 py-1 font-label-ui text-[10px] uppercase tracking-[0.2em] text-white/72">
                    {flow.severity}
                  </div>
                </div>

                <div className="mt-5 rounded-lg border border-white/10 bg-black/40 px-4 py-3 font-label-ui text-[11px] uppercase tracking-[0.18em] text-white/55">
                  {flow.route}
                </div>

                <p className="mt-5 text-sm leading-7 text-white/65">
                  {flow.description}
                </p>

                <div className="mt-6 space-y-4">
                  {flow.decisions.map((item) => (
                    <div key={item} className="flex gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#634BFF]" />
                      <p className="text-sm leading-7 text-white/62">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="contract" className="border-b border-white/8 px-5 py-24 sm:px-8 lg:px-10">
        <div className="mx-auto grid max-w-[1500px] gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <div className="font-label-ui text-[11px] uppercase tracking-[0.34em] text-white/42">
              Canonical incident record
            </div>
            <h2 className="mt-4 font-display text-4xl font-black uppercase tracking-[-0.03em] sm:text-5xl">
              Every agent and operator works from the same object.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-white/62">
              DeepOps does not pass opaque handoffs between tools. It maintains
              one canonical incident record with lifecycle state, diagnosis,
              fix, approval, deployment, and timeline context.
            </p>

            <div className="mt-8 grid gap-3 rounded-2xl border border-white/10 bg-[#05070d] p-6 font-label-ui text-[12px] tracking-[0.08em] text-white/76">
              {schemaPreview.map((line) => (
                <div
                  key={line}
                  className="border-b border-white/6 pb-3 last:border-b-0 last:pb-0"
                >
                  {line}
                </div>
              ))}
            </div>

            <div className="mt-8 flex flex-wrap gap-2">
              {lifecycleStates.map((state) => (
                <span
                  key={state}
                  className="rounded-full border border-white/10 px-3 py-2 font-label-ui text-[10px] uppercase tracking-[0.18em] text-white/58"
                >
                  {state}
                </span>
              ))}
            </div>
          </div>

          <div className="grid gap-6">
            <div className="glass-panel rounded-2xl p-7">
              <div className="font-label-ui text-[11px] uppercase tracking-[0.3em] text-white/42">
                Frontend contract
              </div>
              <div className="mt-4 font-display text-2xl font-bold uppercase tracking-tight">
                The dashboard is a live operator surface, not a fake mock.
              </div>
              <div className="mt-6 space-y-4">
                {dashboardCapabilities.map((item) => (
                  <div key={item} className="flex gap-3">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#10B981]" />
                    <p className="text-sm leading-7 text-white/64">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-panel rounded-2xl p-7">
              <div className="font-label-ui text-[11px] uppercase tracking-[0.3em] text-white/42">
                Live API surfaces
              </div>
              <div className="mt-6 grid gap-3">
                {apiSurfaces.map((route) => (
                  <div
                    key={route}
                    className="rounded-lg border border-white/8 bg-black/45 px-4 py-3 font-label-ui text-[11px] uppercase tracking-[0.16em] text-white/68"
                  >
                    {route}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden px-5 py-28 sm:px-8 lg:px-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,75,255,0.14),transparent_42%)]" />
        <div className="relative mx-auto max-w-5xl text-center">
          <div className="font-label-ui text-[11px] uppercase tracking-[0.38em] text-white/45">
            Mission-ready demo
          </div>
          <h2 className="mt-6 font-display text-5xl font-black uppercase tracking-[-0.04em] sm:text-7xl">
            Break the app. Let the system answer.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-white/64 sm:text-lg">
            The landing page should set up exactly what the judges will see:
            live incidents, human approval when risk climbs, and phone
            escalation when the operator has to be pulled back into the loop.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="trigger-glow inline-flex items-center rounded-sm bg-[linear-gradient(135deg,#634BFF_0%,#8B5CF6_100%)] px-8 py-4 font-display text-base font-bold uppercase tracking-[0.08em] text-white transition hover:brightness-110"
            >
              Launch Dashboard
            </Link>
            <a
              href="#flows"
              className="inline-flex items-center rounded-sm border border-white/12 px-8 py-4 font-display text-base font-bold uppercase tracking-[0.08em] text-white/82 transition hover:border-white/28 hover:text-white"
            >
              Review Demo Paths
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
