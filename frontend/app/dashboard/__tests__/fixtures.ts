import type { Incident } from "../types";

export const mockIncidentPending: Incident = {
  incident_id: "inc-abc12345-def67890",
  status: "awaiting_approval",
  severity: "high",
  service: "payment-api",
  environment: "production",
  created_at_ms: Date.now() - 300_000,
  updated_at_ms: Date.now() - 60_000,
  source: {
    error_type: "NullPointerException",
    error_message: "Cannot read property 'id' of null",
    source_file: "src/handlers/payment.ts",
  },
  diagnosis: {
    status: "complete",
    root_cause: "Missing null check in payment handler",
    confidence: 0.92,
    suggested_fix: "Add null guard before accessing payment.id",
  },
  fix: {
    status: "complete",
    diff_preview:
      "--- a/src/handlers/payment.ts\n+++ b/src/handlers/payment.ts\n@@ -15,6 +15,9 @@\n   const payment = await getPayment(id);\n+  if (!payment) {\n+    throw new NotFoundError('Payment not found');\n+  }\n   return payment.id;",
    files_changed: ["src/handlers/payment.ts"],
    spec_markdown: "## Fix Spec\nAdd null guard for payment lookup",
    test_plan: [
      "Test with valid payment ID",
      "Test with non-existent payment ID",
    ],
  },
  approval: {
    required: true,
    mode: "manual",
    status: "pending",
    channel: null,
    decider: null,
    bland_call_id: null,
    notes: null,
    decision_at_ms: null,
  },
  timeline: [],
};

export const mockIncidentResolved: Incident = {
  ...mockIncidentPending,
  incident_id: "inc-resolved-001",
  status: "resolved",
  severity: "low",
  approval: {
    ...mockIncidentPending.approval,
    status: "approved",
    decision_at_ms: Date.now() - 30_000,
  },
};
