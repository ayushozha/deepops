import Link from "next/link";

const serverRackImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAIY4X50c9R-Yd2gJkhMiSDs9rf4l0Q-tQZ-8aJcGUHOlsGpwb2bRFe46nt6e_8YyCJ3o2D7yRSREefL59vAWsZCVobWUKuaNu7o4WGSPxWRP6y7_JGvGD1hKMvEHW7dcd8LcpaAFVL79qad8no2gCxHZupXqcwh9JZT8HR1BRBh8ZgsRM8lfyHppqtgjZik_tvOanSf6qyStSffU4ORcJH4dNUqVLuXuFUbn4-solk44gllDWpFZX1sIUQwldGi-4_5AQ1GG6NjPs";

const heroRailItems = [
  { key: "command", active: true },
  { key: "logs", active: false },
  { key: "metrics", active: false },
  { key: "archive", active: false },
] as const;

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

function RailIcon({ icon }: { icon: (typeof heroRailItems)[number]["key"] }) {
  const className = "h-6 w-6";

  if (icon === "command") {
    return (
      <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
        <path
          d="M5 6h14v12H5z"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
        <path
          d="m8 11 2 2-2 2M12.5 15H16"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (icon === "logs") {
    return (
      <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
        <path
          d="M7 4h10v16H7zM9 2v4M15 2v4M9 10h6M9 14h6M9 18h4"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (icon === "metrics") {
    return (
      <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
        <path
          d="M5 19V9M12 19V5M19 19v-8"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
        />
        <path
          d="M4 19h16"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M6 7h12M7 7v11h10V7M9 11h6"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 4h6"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-black text-white">
      <div className="scanline-overlay" />

      <section className="border-b border-white/8 px-3 pt-3 pb-10 sm:px-4">
        <div className="mx-auto overflow-hidden rounded-[26px] border border-[#634BFF]/30 bg-black shadow-[0_0_0_1px_rgba(99,75,255,0.08),0_18px_60px_rgba(0,0,0,0.55)]">
          <div className="flex h-20 items-center justify-between border-b border-[#634BFF]/25 px-8 sm:px-10">
            <div className="font-display text-[2rem] font-black uppercase tracking-[-0.05em] text-[#5f45ff]">
              NOC CONTROL
            </div>

            <div className="hidden items-center md:flex">
              <span className="border-b-2 border-[#634BFF] pb-1 font-display text-[2rem] font-bold tracking-[-0.05em] text-[#5f45ff]">
                Mission Status: Active
              </span>
            </div>

            <a
              href="#flows"
              className="trigger-glow inline-flex h-11 items-center justify-center rounded-[2px] bg-[linear-gradient(135deg,#634BFF_0%,#8E6CFF_100%)] px-6 font-label-ui text-[0.8rem] uppercase tracking-[0.28em] text-white transition hover:brightness-110"
            >
              Trigger Bug
            </a>
          </div>

          <div className="grid min-h-[calc(100svh-120px)] grid-cols-[94px_minmax(0,1fr)]">
            <aside className="border-r border-[#634BFF]/15 bg-black pt-20">
              <div className="flex flex-col gap-6">
                {heroRailItems.map((item) => (
                  <div
                    key={item.key}
                    className={`flex h-[68px] items-center justify-center transition ${
                      item.active
                        ? "bg-[#1a1a1a] text-[#634BFF]"
                        : "text-white/75"
                    }`}
                  >
                    <RailIcon icon={item.key} />
                  </div>
                ))}
              </div>
            </aside>

            <div className="relative min-h-0 overflow-hidden">
              <div
                className="absolute inset-0 bg-cover bg-center opacity-33"
                style={{ backgroundImage: `url('${serverRackImage}')` }}
              />
              <div className="absolute inset-0 bg-[linear-gradient(90deg,#000000_0%,#000000_37%,rgba(0,0,0,0.84)_50%,rgba(0,0,0,0.62)_64%,rgba(14,7,25,0.76)_100%)]" />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,75,255,0.16),transparent_36%)]" />
              <div className="absolute inset-y-0 left-[33%] hidden w-px bg-white/6 lg:block" />

              <div className="relative z-10 flex min-h-0 items-end">
                <div className="w-full max-w-[760px] px-10 pb-10 pt-14 sm:px-16 lg:px-20">
                  <div className="mb-6 inline-flex items-center gap-3 rounded-full border border-[#634BFF]/25 bg-[#634BFF]/6 px-5 py-2.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#634BFF]" />
                    <span className="font-label-ui text-[0.72rem] uppercase tracking-[0.38em] text-[#8B7CFF]">
                      System Integrity: Nominal
                    </span>
                  </div>

                  <h1 className="font-display text-[3.5rem] font-black leading-[0.92] tracking-[-0.08em] text-white sm:text-[4.5rem] xl:text-[5.5rem]">
                    <span className="block">The </span>
                    <span className="block bg-[linear-gradient(90deg,#7DE4FF_0%,#C55CFF_55%,#654BFF_100%)] bg-clip-text text-transparent">
                      Self-Healing
                    </span>
                    <span className="block">Codebase Agent</span>
                  </h1>

                  <p className="mt-6 max-w-[700px] text-[1.05rem] leading-[1.7] text-white/62 sm:text-[1.15rem]">
                    DeepOps gives your team an autonomous command layer that
                    monitors live failures, diagnoses root cause, drafts the
                    remediation path, and only breaks the glass when a human
                    decision is actually needed.
                  </p>

                  <div className="mt-8 flex flex-wrap gap-5">
                    <Link
                      href="/dashboard"
                      className="inline-flex min-h-[56px] min-w-[260px] items-center justify-center rounded-[2px] bg-[linear-gradient(135deg,#634BFF_0%,#7B5CFF_100%)] px-6 font-display text-[0.95rem] font-bold tracking-[-0.03em] text-white transition hover:brightness-110"
                    >
                      Deploy Mission Control
                    </Link>
                    <a
                      href="#contract"
                      className="inline-flex min-h-[56px] min-w-[260px] items-center justify-center rounded-[2px] border border-white/10 bg-transparent px-6 font-display text-[0.95rem] font-bold tracking-[-0.03em] text-white transition hover:border-white/24 hover:bg-white/[0.03]"
                    >
                      Read Documentation
                    </a>
                  </div>

                  <div className="mt-10 flex flex-wrap gap-10 font-label-ui text-[0.74rem] uppercase tracking-[0.28em]">
                    <div>
                      <div className="mb-3 text-[#73DAFF]">Latency</div>
                      <div className="text-[1rem] tracking-[0.16em] text-white">
                        1.2ms
                      </div>
                    </div>
                    <div>
                      <div className="mb-3 text-[#D873FF]">Uptime</div>
                      <div className="text-[1rem] tracking-[0.16em] text-white">
                        99.999%
                      </div>
                    </div>
                    <div>
                      <div className="mb-3 text-[#634BFF]">Threats</div>
                      <div className="text-[1rem] tracking-[0.16em] text-white">
                        0 Neutralized
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
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
