import { apiGet } from "./client";
import type { HealthResponse } from "../types/api";

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health", signal);
}
