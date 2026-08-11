import { useEffect, useState } from "react";
import { fetchHealth } from "../api/health";
import { ApiConfigurationError } from "../api/client";

export type HealthCheckState =
  | { status: "loading" }
  | { status: "ok" }
  | { status: "error"; message: string };

export function useHealthCheck(): HealthCheckState {
  const [state, setState] = useState<HealthCheckState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then(() => setState({ status: "ok" }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiConfigurationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "No se pudo contactar al backend.";
        setState({ status: "error", message });
      });

    return () => controller.abort();
  }, []);

  return state;
}
