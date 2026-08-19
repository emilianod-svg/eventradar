import { useEffect, useState } from "react";
import { ApiConfigurationError } from "../api/client";
import { fetchCycleDetail, type ExecutionDetail } from "../api/cycles";

export type CycleDetailState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; item: ExecutionDetail }
  | { status: "error"; message: string };

export function useCycleDetail(adminApiKey: string, executionId: string | null, refreshKey = 0): CycleDetailState {
  const [state, setState] = useState<CycleDetailState>({ status: "idle" });

  useEffect(() => {
    if (!adminApiKey.trim() || !executionId) {
      setState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });

    fetchCycleDetail(adminApiKey, executionId, controller.signal)
      .then((item) => {
        if (controller.signal.aborted) return;
        setState({ status: "ready", item });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiConfigurationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "No se pudo cargar el detalle del ciclo.";
        setState({ status: "error", message });
      });

    return () => controller.abort();
  }, [adminApiKey, executionId, refreshKey]);

  return state;
}
