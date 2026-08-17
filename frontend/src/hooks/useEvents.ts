import { useEffect, useState } from "react";
import { fetchEvents } from "../api/events";
import { ApiConfigurationError } from "../api/client";
import type { EventItem } from "../types/api";

export type EventsState =
  | { status: "loading" }
  | { status: "ready"; items: EventItem[] }
  | { status: "error"; message: string };

export function useEvents(): EventsState {
  const [state, setState] = useState<EventsState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchEvents(controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setState({ status: "ready", items: response.items });
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
  }, []);

  return state;
}
