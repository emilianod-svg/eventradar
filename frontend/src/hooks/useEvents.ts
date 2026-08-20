import { useEffect, useState } from "react";
import { fetchEvents } from "../api/events";
import { ApiConfigurationError } from "../api/client";
import type { PaginatedEvents } from "../types/api";
import type { EventQuery } from "../api/events";

export type EventsState =
  | { status: "loading" }
  | (PaginatedEvents & { status: "ready" })
  | { status: "error"; message: string };

export function useEvents(query: EventQuery, refreshKey = 0): EventsState {
  const [state, setState] = useState<EventsState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    setState({ status: "loading" });

    fetchEvents(query, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setState({ status: "ready", ...response });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiConfigurationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "No se pudieron cargar los eventos.";
        setState({ status: "error", message });
      });

    return () => controller.abort();
  }, [query, refreshKey]);

  return state;
}
