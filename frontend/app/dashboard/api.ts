import type { ApprovalDecisionResponse, HealthResponse, Incident } from "./types";

export async function buildApiError(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`.trim();

  try {
    const payload = (await response.json()) as Record<string, unknown>;
    const detail = payload.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }

          if (
            item &&
            typeof item === "object" &&
            "msg" in item &&
            typeof item.msg === "string"
          ) {
            return item.msg;
          }

          return JSON.stringify(item);
        })
        .join(", ");
    }

    if (typeof payload.error === "string" && payload.error.trim()) {
      return payload.error;
    }
  } catch {
    return fallback;
  }

  return fallback;
}

export async function fetchIncidentList(): Promise<Incident[]> {
  const response = await fetch("/api/incidents", {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiError(response));
  }

  return (await response.json()) as Incident[];
}

export async function fetchIncidentDetail(incidentId: string): Promise<Incident> {
  const response = await fetch(`/api/incidents/${encodeURIComponent(incidentId)}`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiError(response));
  }

  return (await response.json()) as Incident;
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health", {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await buildApiError(response));
  }

  return (await response.json()) as HealthResponse;
}

export async function submitApprovalDecision(
  incidentId: string,
  body: Record<string, unknown>,
): Promise<ApprovalDecisionResponse> {
  const response = await fetch(
    `/api/approval/${encodeURIComponent(incidentId)}/decision`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    throw new Error(await buildApiError(response));
  }

  return (await response.json()) as ApprovalDecisionResponse;
}
