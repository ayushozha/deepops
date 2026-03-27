import type { Incident } from "../types";
import { Metric, Panel, Pill, SectionHeader } from "./dashboard-ui";

type DiffLine = {
  kind: "header" | "add" | "remove" | "context";
  text: string;
};

function parseDiff(diffPreview: string | null): DiffLine[] {
  if (!diffPreview) {
    return [];
  }

  return diffPreview.split("\n").map((line) => {
    if (line.startsWith("@@") || line.startsWith("+++") || line.startsWith("---")) {
      return { kind: "header", text: line };
    }
    if (line.startsWith("+")) {
      return { kind: "add", text: line };
    }
    if (line.startsWith("-")) {
      return { kind: "remove", text: line };
    }
    return { kind: "context", text: line };
  });
}

function confidenceLabel(value: number | null) {
  if (value === null) {
    return "Pending";
  }

  return `${Math.round(value * 100)}%`;
}

export function DiffViewer({ incident }: { incident: Incident | null }) {
  if (!incident) {
    return (
      <Panel className="flex h-full min-h-[34rem] items-center justify-center">
        <div className="max-w-md px-8 py-12 text-center">
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-cyan-200/70">
            diff viewer
          </p>
          <p className="mt-4 text-2xl font-semibold text-white">
            Select an incident to inspect the generated patch.
          </p>
        </div>
      </Panel>
    );
  }

  const diffLines = parseDiff(incident.fix.diff_preview);

  return (
    <Panel className="flex h-full min-h-[34rem] flex-col overflow-hidden">
      <SectionHeader
        eyebrow="ai diff viewer"
        title="Generated remediation package"
        description="Diagnosis, generated diff, spec, and test guidance are rendered directly from the backend incident contract."
      />

      <div className="min-h-0 flex-1 space-y-5 overflow-auto px-4 py-4 sm:px-5">
        <div className="grid gap-3 md:grid-cols-3">
          <Metric
            label="root cause"
            value={incident.diagnosis.root_cause ?? "Pending diagnosis"}
          />
          <Metric
            label="confidence"
            value={confidenceLabel(incident.diagnosis.confidence)}
          />
          <Metric
            label="approval channel"
            value={incident.approval.channel ?? "manual review"}
          />
        </div>

        {incident.fix.files_changed.length ? (
          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-4">
            <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-slate-500">
              files changed
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {incident.fix.files_changed.map((file) => (
                <Pill key={file} tone="cyan">
                  {file}
                </Pill>
              ))}
            </div>
          </div>
        ) : null}

        <div className="rounded-2xl border border-white/10 bg-[#03101c]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-cyan-200/70">
              unified diff preview
            </p>
            <p className="text-xs text-slate-500">
              {diffLines.length ? "generated patch" : "no diff preview yet"}
            </p>
          </div>
          <div className="overflow-auto">
            <div className="min-w-full font-mono text-sm leading-6">
              {diffLines.length ? (
                diffLines.map((line, index) => (
                  <div
                    key={`${line.text}-${index}`}
                    className={`whitespace-pre px-4 ${
                      line.kind === "header"
                        ? "text-cyan-200/80"
                        : line.kind === "add"
                          ? "bg-emerald-400/10 text-emerald-100"
                          : line.kind === "remove"
                            ? "bg-red-400/10 text-red-100"
                            : "text-slate-300"
                    }`}
                  >
                    {line.text || " "}
                  </div>
                ))
              ) : (
                <div className="px-4 py-6 text-slate-400">
                  No diff preview is available for the selected incident.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-4">
            <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-slate-500">
              fix spec
            </p>
            <details className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <summary className="cursor-pointer font-medium text-white">
                Open spec_markdown
              </summary>
              <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                {incident.fix.spec_markdown ?? "No spec markdown available."}
              </div>
            </details>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-4">
            <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-slate-500">
              guidance
            </p>
            <div className="mt-3 space-y-3 text-sm leading-6 text-slate-300">
              <p>{incident.diagnosis.suggested_fix ?? "No suggested fix."}</p>
              <div>
                <p className="font-mono text-[0.68rem] uppercase tracking-[0.28em] text-slate-500">
                  test plan
                </p>
                {(incident.fix.test_plan ?? []).length ? (
                  <ul className="mt-2 space-y-1">
                    {(incident.fix.test_plan ?? []).map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="text-cyan-300">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-slate-400">
                    No test plan has been attached yet.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
