import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  fetchIncidentList,
  fetchIncidentDetail,
  submitApprovalDecision,
  fetchBackendHealth,
  buildApiError,
} from "../api";
import { mockIncidentPending } from "./fixtures";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

function jsonResponse(body: unknown, status = 200, statusText = "OK") {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: () => Promise.resolve(body),
  } as Response;
}

describe("fetchIncidentList", () => {
  it("returns Incident[] on success", async () => {
    const data = [mockIncidentPending];
    mockFetch.mockResolvedValueOnce(jsonResponse(data));

    const result = await fetchIncidentList();
    expect(result).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith("/api/incidents", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  });

  it("throws with detail message on error response", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Not authorized" }, 403, "Forbidden"),
    );

    await expect(fetchIncidentList()).rejects.toThrow("Not authorized");
  });
});

describe("fetchIncidentDetail", () => {
  it("returns a single Incident on success", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(mockIncidentPending));

    const result = await fetchIncidentDetail("inc-abc12345-def67890");
    expect(result).toEqual(mockIncidentPending);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/incidents/inc-abc12345-def67890",
      {
        cache: "no-store",
        headers: { Accept: "application/json" },
      },
    );
  });

  it("throws on error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Incident not found" }, 404, "Not Found"),
    );

    await expect(fetchIncidentDetail("bad-id")).rejects.toThrow(
      "Incident not found",
    );
  });
});

describe("submitApprovalDecision", () => {
  it("sends correct POST body and returns response", async () => {
    const responseBody = {
      processed: true,
      incident: mockIncidentPending,
      flow: {
        action: "approve",
        mode: "manual",
        reason: "user approved",
        next_status: "deploying",
        requires_human: false,
        should_call_human: false,
      },
      policy: {
        severity: "high",
        required: true,
        mode: "manual",
        status: "approved",
        route: "dashboard",
        next_action: "deploy",
        channel: null,
        decider: null,
        reason: "user approved",
        requires_phone_escalation: false,
      },
      auth0_context: {},
      explanations: {},
    };
    mockFetch.mockResolvedValueOnce(jsonResponse(responseBody));

    const body = { approved: true, decision: "approve", notes: "Looks good" };
    const result = await submitApprovalDecision("inc-abc12345-def67890", body);
    expect(result).toEqual(responseBody);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/approval/inc-abc12345-def67890/decision",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      },
    );
  });

  it("throws on error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Invalid decision" }, 400, "Bad Request"),
    );

    await expect(
      submitApprovalDecision("inc-abc", { approved: true }),
    ).rejects.toThrow("Invalid decision");
  });
});

describe("fetchBackendHealth", () => {
  it("returns HealthResponse on success", async () => {
    const healthData = {
      ok: true,
      service: "deepops",
      environment: "production",
      backend: "live",
      store: "redis",
    };
    mockFetch.mockResolvedValueOnce(jsonResponse(healthData));

    const result = await fetchBackendHealth();
    expect(result).toEqual(healthData);
    expect(mockFetch).toHaveBeenCalledWith("/api/health", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  });

  it("throws on error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: "Service unavailable" }, 503, "Service Unavailable"),
    );

    await expect(fetchBackendHealth()).rejects.toThrow("Service unavailable");
  });
});

describe("buildApiError", () => {
  it("extracts string detail from response", async () => {
    const response = jsonResponse(
      { detail: "Custom error message" },
      400,
      "Bad Request",
    );
    const msg = await buildApiError(response);
    expect(msg).toBe("Custom error message");
  });

  it("extracts array detail with string items", async () => {
    const response = jsonResponse(
      { detail: ["Error one", "Error two"] },
      422,
      "Unprocessable",
    );
    const msg = await buildApiError(response);
    expect(msg).toBe("Error one, Error two");
  });

  it("extracts array detail with msg objects", async () => {
    const response = jsonResponse(
      { detail: [{ msg: "Field required", loc: ["body", "name"] }] },
      422,
      "Unprocessable",
    );
    const msg = await buildApiError(response);
    expect(msg).toBe("Field required");
  });

  it("extracts error field when no detail", async () => {
    const response = jsonResponse(
      { error: "Something broke" },
      500,
      "Internal Server Error",
    );
    const msg = await buildApiError(response);
    expect(msg).toBe("Something broke");
  });

  it("falls back to status text when json parsing fails", async () => {
    const response = {
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: () => Promise.reject(new Error("not json")),
    } as Response;
    const msg = await buildApiError(response);
    expect(msg).toBe("502 Bad Gateway");
  });

  it("falls back to status text when no detail or error in json", async () => {
    const response = jsonResponse({ foo: "bar" }, 500, "Internal Server Error");
    const msg = await buildApiError(response);
    expect(msg).toBe("500 Internal Server Error");
  });
});
