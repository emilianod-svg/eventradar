import { useEffect, useState } from "react";
import { ApiConfigurationError } from "../api/client";
import { fetchEvent } from "../api/events";
import type { EventItem } from "../types/api";

export type EventDetailState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; event: EventItem }
  | { status: "error"; message: string };

export function useEventDetail(
  slug: string | null,
  fallbackEvent: EventItem | null,
  refreshKey = 0
): EventDetailState {
  const [state, setState] = useState<EventDetailState>(() => {
    if (fallbackEvent) {
      return { status: "ready", event: fallbackEvent };
    }

    return { status: "idle" };
  });

  useEffect(() => {
    if (!slug) {
      setState({ status: "idle" });
      return;
    }

    if (fallbackEvent) {
      setState({ status: "ready", event: fallbackEvent });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });

    fetchEvent(slug, controller.signal)
      .then((event) => {
        if (controller.signal.aborted) return;
        setState({ status: "ready", event });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiConfigurationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "No se pudo cargar el detalle del evento.";
        setState({ status: "error", message });
      });

    return () => controller.abort();
  }, [fallbackEvent, refreshKey, slug]);

  return state;
}
