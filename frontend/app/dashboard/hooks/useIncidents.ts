"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { fetchIncidentDetail, fetchIncidentList } from "../api";
import type {
  Incident,
  IncidentStreamEvent,
  StreamConnectionState,
} from "../types";

const DEFAULT_POLL_INTERVAL_MS = 7_500;

type RefreshIncidentsOptions = {
  background?: boolean;
  preserveSelection?: boolean;
};

type UseIncidentsOptions = {
  autoSelectFirst?: boolean;
  pollIntervalMs?: number;
};

function getIncidentSortTime(incident: Incident): number {
  return incident.updated_at_ms ?? incident.created_at_ms ?? 0;
}

function sortIncidents(incidents: Incident[]): Incident[] {
  return [...incidents].sort((left, right) => {
    return getIncidentSortTime(right) - getIncidentSortTime(left);
  });
}

function mergeIncident(incidents: Incident[], nextIncident: Incident): Incident[] {
  const deduped = incidents.filter(
    (incident) => incident.incident_id !== nextIncident.incident_id,
  );

  return sortIncidents([...deduped, nextIncident]);
}

function parseStreamPayload(event: Event): IncidentStreamEvent | null {
  const messageEvent = event as MessageEvent<string>;

  if (!messageEvent.data) {
    return null;
  }

  try {
    return JSON.parse(messageEvent.data) as IncidentStreamEvent;
  } catch {
    return null;
  }
}

export function useIncidents(options: UseIncidentsOptions = {}) {
  const {
    autoSelectFirst = false,
    pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  } = options;

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamState, setStreamState] =
    useState<StreamConnectionState>("connecting");

  const isMountedRef = useRef(false);
  const requestInFlightRef = useRef(false);

  const mergeIncomingIncident = useCallback((incident: Incident) => {
    startTransition(() => {
      setIncidents((current) => mergeIncident(current, incident));
      setError(null);
      setSelectedIncidentId((current) => {
        if (current) {
          return current;
        }

        return autoSelectFirst ? incident.incident_id : null;
      });
    });
  }, [autoSelectFirst]);

  const refreshIncidents = useCallback(
    async (refreshOptions: RefreshIncidentsOptions = {}) => {
      const { background = false, preserveSelection = true } = refreshOptions;

      if (requestInFlightRef.current) {
        return;
      }

      requestInFlightRef.current = true;

      if (background) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      try {
        const nextIncidents = sortIncidents(await fetchIncidentList());

        if (!isMountedRef.current) {
          return;
        }

        startTransition(() => {
          setIncidents(nextIncidents);
          setError(null);
          setSelectedIncidentId((current) => {
            if (preserveSelection && current) {
              const stillExists = nextIncidents.some(
                (incident) => incident.incident_id === current,
              );

              if (stillExists) {
                return current;
              }
            }

            return autoSelectFirst ? nextIncidents[0]?.incident_id ?? null : null;
          });
        });
      } catch (caughtError) {
        if (!isMountedRef.current) {
          return;
        }

        const message =
          caughtError instanceof Error
            ? caughtError.message
            : "Failed to fetch incidents.";
        setError(message);
      } finally {
        if (isMountedRef.current) {
          setIsLoading(false);
          setIsRefreshing(false);
        }

        requestInFlightRef.current = false;
      }
    },
    [autoSelectFirst],
  );

  const refreshSelectedIncident = useCallback(
    async (incidentId?: string) => {
      const targetIncidentId = incidentId ?? selectedIncidentId;

      if (!targetIncidentId) {
        return null;
      }

      try {
        const incident = await fetchIncidentDetail(targetIncidentId);

        if (!isMountedRef.current) {
          return null;
        }

        mergeIncomingIncident(incident);
        return incident;
      } catch (caughtError) {
        if (!isMountedRef.current) {
          return null;
        }

        const message =
          caughtError instanceof Error
            ? caughtError.message
            : "Failed to refresh incident detail.";
        setError(message);
        return null;
      }
    },
    [mergeIncomingIncident, selectedIncidentId],
  );

  useEffect(() => {
    isMountedRef.current = true;
    setStreamState("connecting");

    void refreshIncidents({ preserveSelection: false });

    const eventSource = new EventSource("/api/incidents/stream");

    const handleIncidentEvent: EventListener = (event) => {
      const payload = parseStreamPayload(event);

      if (!payload || !payload.incident) {
        return;
      }

      mergeIncomingIncident(payload.incident);
    };

    const handleStreamOpen = () => {
      setStreamState("live");
      void refreshIncidents({ background: true });
    };

    const handleStreamError = () => {
      setStreamState("degraded");
    };

    const handleFocus = () => {
      void refreshIncidents({ background: true });
    };

    eventSource.addEventListener("open", handleStreamOpen);
    eventSource.addEventListener("error", handleStreamError);
    eventSource.addEventListener("incident.created", handleIncidentEvent);
    eventSource.addEventListener("incident.updated", handleIncidentEvent);

    const intervalId = window.setInterval(() => {
      void refreshIncidents({ background: true });
    }, pollIntervalMs);

    window.addEventListener("focus", handleFocus);

    return () => {
      isMountedRef.current = false;
      setStreamState("closed");
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleFocus);
      eventSource.removeEventListener("open", handleStreamOpen);
      eventSource.removeEventListener("error", handleStreamError);
      eventSource.removeEventListener("incident.created", handleIncidentEvent);
      eventSource.removeEventListener("incident.updated", handleIncidentEvent);
      eventSource.close();
    };
  }, [mergeIncomingIncident, pollIntervalMs, refreshIncidents]);

  const selectedIncident =
    incidents.find((incident) => incident.incident_id === selectedIncidentId) ?? null;

  return {
    incidents,
    selectedIncidentId,
    selectedIncident,
    isLoading,
    isRefreshing,
    error,
    streamState,
    setSelectedIncidentId,
    replaceIncident: mergeIncomingIncident,
    refreshIncidents,
    refreshSelectedIncident,
  };
}
