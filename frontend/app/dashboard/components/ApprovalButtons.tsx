import type { Incident } from "../types";
import { Panel, Pill, SectionHeader } from "./dashboard-ui";

export function ApprovalButtons({
  incident,
  isSubmitting = false,
  error = null,
  onApprove,
  onReject,
}: {
  incident: Incident | null;
  isSubmitting?: boolean;
  error?: string | null;
  onApprove: () => void;
  onReject: () => void;
}) {
  const requiresDecision =
    incident?.status === "awaiting_approval" &&
    incident.approval.status === "pending";

  return (
    <Panel className="overflow-hidden">
      <SectionHeader
        eyebrow="approval gate"
        title="Human decision controls"
        description="Approve or reject only when the selected incident is awaiting manual approval."
      />

      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-6">
        <div className="space-y-2">
          <p className="text-sm text-slate-300">
            {incident
              ? requiresDecision
                ? "Approval is required for this incident."
                : "Approval has already been handled for the current selection."
              : "Choose an incident to see the approval gate."}
          </p>
          {incident ? (
            <Pill tone={incident.approval.status === "pending" ? "orange" : "green"}>
              {incident.approval.status}
            </Pill>
          ) : null}
          {error ? <p className="text-sm text-red-200">{error}</p> : null}
        </div>

        {incident && requiresDecision ? (
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onApprove}
              disabled={isSubmitting}
              className="rounded-full border border-emerald-300/40 bg-emerald-300/10 px-5 py-3 font-mono text-sm uppercase tracking-[0.22em] text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "SUBMITTING" : "APPROVE"}
            </button>
            <button
              type="button"
              onClick={onReject}
              disabled={isSubmitting}
              className="rounded-full border border-red-300/40 bg-red-300/10 px-5 py-3 font-mono text-sm uppercase tracking-[0.22em] text-red-100 transition hover:bg-red-300/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "SUBMITTING" : "REJECT"}
            </button>
          </div>
        ) : (
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-slate-500">
            No action required
          </p>
        )}
      </div>
    </Panel>
  );
}
