"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchBackendHealth } from "../api";
import type { BackendHealthState, HealthResponse } from "../types";

const DEFAULT_HEALTH_POLL_INTERVAL_MS = 10_000;

type UseBackendHealthOptions = {
  pollIntervalMs?: number;
};

export function useBackendHealth(
  options: UseBackendHealthOptions = {},
) {
  const { pollIntervalMs = DEFAULT_HEALTH_POLL_INTERVAL_MS } = options;
  const isMountedRef = useRef(false);
  const requestInFlightRef = useRef(false);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<BackendHealthState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null);

  const runHealthCheck = useCallback(async () => {
    if (requestInFlightRef.current) {
      return;
    }

    requestInFlightRef.current = true;

    try {
      const nextHealth = await fetchBackendHealth();

      if (!isMountedRef.current) {
        return;
      }

      setHealth(nextHealth);
      setStatus(nextHealth.ok ? "live" : "degraded");
      setError(nextHealth.ok ? null : nextHealth.error ?? "Backend health degraded.");
      setLastCheckedAt(Date.now());
    } catch (caughtError) {
      if (!isMountedRef.current) {
        return;
      }

      const message =
        caughtError instanceof Error
          ? caughtError.message
          : "Failed to fetch backend health.";
      setStatus("offline");
      setError(message);
      setLastCheckedAt(Date.now());
    } finally {
      requestInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    void runHealthCheck();

    const intervalId = window.setInterval(() => {
      void runHealthCheck();
    }, pollIntervalMs);

    const handleFocus = () => {
      void runHealthCheck();
    };

    window.addEventListener("focus", handleFocus);

    return () => {
      isMountedRef.current = false;
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
    };
    // runHealthCheck is a stable useCallback (empty deps) — no need to list it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollIntervalMs]);

  return {
    health,
    status,
    error,
    lastCheckedAt,
    refresh: runHealthCheck,
  };
}
