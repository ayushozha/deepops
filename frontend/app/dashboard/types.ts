export type IncidentStatus =
  | "detected"
  | "stored"
  | "diagnosing"
  | "fixing"
  | "gating"
  | "awaiting_approval"
  | "deploying"
  | "resolved"
  | "blocked"
  | "failed";

export type IncidentSeverity =
  | "pending"
  | "low"
  | "medium"
  | "high"
  | "critical";

export type DiagnosisStatus = "pending" | "running" | "complete" | "failed";
export type FixStatus = "pending" | "running" | "complete" | "failed";
export type ApprovalStatus = "pending" | "approved" | "rejected" | string;
export type StreamEventName =
  | "incident.created"
  | "incident.updated"
  | "pipeline.heartbeat";

export type IncidentTimelineEvent = {
  at_ms: number;
  status: string;
  actor: string;
  message: string;
  sponsor?: string;
  metadata?: Record<string, unknown> | null;
};

export type IncidentSource = {
  provider?: string;
  path?: string;
  error_type: string;
  error_message: string;
  source_file: string;
  timestamp_ms?: number;
  fingerprint?: string | null;
  raw_payload?: Record<string, unknown> | null;
};

export type IncidentDiagnosis = {
  status: DiagnosisStatus;
  root_cause: string | null;
  suggested_fix?: string | null;
  affected_components?: string[] | null;
  confidence: number | null;
  severity_reasoning?: string | null;
  macroscope_context?: string | null;
  started_at_ms?: number | null;
  completed_at_ms?: number | null;
};

export type IncidentFix = {
  status: FixStatus;
  diff_preview: string | null;
  files_changed: string[];
  spec_markdown: string | null;
  test_plan?: string[];
  started_at_ms?: number | null;
  completed_at_ms?: number | null;
};

export type IncidentApproval = {
  required: boolean;
  mode: string;
  status: ApprovalStatus;
  channel: string | null;
  decider: string | null;
  bland_call_id: string | null;
  notes: string | null;
  decision_at_ms: number | null;
};

export type IncidentDeployment = {
  provider?: string;
  status?: string;
  service_name?: string | null;
  environment?: string | null;
  commit_sha?: string | null;
  deploy_url?: string | null;
  started_at_ms?: number | null;
  completed_at_ms?: number | null;
  failure_reason?: string | null;
};

export type Incident = {
  incident_id: string;
  title?: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  service: string;
  environment: string;
  created_at_ms: number;
  updated_at_ms: number;
  resolution_time_ms?: number | null;
  source: IncidentSource;
  diagnosis: IncidentDiagnosis;
  fix: IncidentFix;
  approval: IncidentApproval;
  deployment?: IncidentDeployment;
  observability?: Record<string, unknown>;
  timeline: IncidentTimelineEvent[];
  [key: string]: unknown;
};

export type IncidentStreamEvent = {
  event: StreamEventName | string;
  sent_at_ms: number;
  incident_id: string | null;
  status: string | null;
  severity: string | null;
  updated_at_ms: number | null;
  timeline_event: IncidentTimelineEvent | null;
  incident: Incident | null;
  ok?: true;
};

export type ApprovalDecisionBody = {
  approved?: boolean;
  decision?: string;
  notes?: string | null;
  channel?: string | null;
  decider?: string | null;
  actor?: string;
  sponsor?: string;
  mode?: string;
  suggested_steps?: string[];
  constraints?: string[];
};

export type ApprovalDecisionFlow = {
  action: string;
  mode: string;
  reason: string;
  next_status: string | null;
  requires_human: boolean;
  should_call_human: boolean;
};

export type ApprovalDecisionPolicy = {
  severity: string;
  required: boolean;
  mode: string;
  status: string;
  route: string;
  next_action: string;
  channel: string | null;
  decider: string | null;
  reason: string;
  requires_phone_escalation: boolean;
};

export type ApprovalDecisionResponse = {
  processed: boolean;
  incident: Incident;
  flow: ApprovalDecisionFlow;
  policy: ApprovalDecisionPolicy;
  auth0_context: Record<string, unknown>;
  explanations: Record<string, unknown>;
  execution_package?: Record<string, unknown> | null;
  hotfix_package?: Record<string, unknown> | null;
  human_input?: Record<string, unknown> | null;
  [key: string]: unknown;
};

export type HealthResponse = {
  ok: boolean;
  service: string;
  environment: string;
  backend: string;
  store: string;
  sample_count?: number;
  error?: string;
  demo_app?: {
    base_url?: string;
    fallback_mode?: boolean;
  };
  airbyte?: {
    api_url?: string;
    fallback_mode?: boolean;
  };
  [key: string]: unknown;
};

export type StreamConnectionState = "connecting" | "live" | "degraded" | "closed";
export type BackendHealthState = "loading" | "live" | "degraded" | "offline";
