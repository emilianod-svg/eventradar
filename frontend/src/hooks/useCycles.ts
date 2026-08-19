import { useEffect, useState } from "react";
import { ApiConfigurationError } from "../api/client";
import { fetchCycles, type ExecutionItem } from "../api/cycles";

export type CyclesState =
  | { status: "missing-key" }
  | { status: "loading" }
  | { status: "ready"; items: ExecutionItem[] }
  | { status: "error"; message: string };

export function useCycles(adminApiKey: string, refreshKey = 0): CyclesState {
  const [state, setState] = useState<CyclesState>({ status: "missing-key" });

  useEffect(() => {
    if (!adminApiKey.trim()) {
      setState({ status: "missing-key" });
      return;
    }

    const controller = new AbortController();
    let timeoutId: number | undefined;

    const loadCycles = async () => {
      setState((current) => (current.status === "ready" ? current : { status: "loading" }));

      try {
        const items = await fetchCycles(adminApiKey, controller.signal);
        if (controller.signal.aborted) return;
        setState({ status: "ready", items });
      } catch (error: unknown) {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiConfigurationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "No se pudieron cargar los ciclos.";
        setState({ status: "error", message });
      }
    };

    const scheduleRefresh = () => {
      timeoutId = window.setTimeout(async () => {
        await loadCycles();
        if (!controller.signal.aborted) {
          scheduleRefresh();
        }
      }, 10000);
    };

    void loadCycles().then(() => {
      if (!controller.signal.aborted) {
        scheduleRefresh();
      }
    });

    return () => {
      controller.abort();
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [adminApiKey, refreshKey]);

  return state;
}
