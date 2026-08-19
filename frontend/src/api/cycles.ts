import { apiGet, apiPost } from "./client";

export interface ExecutionMetrics {
  sources_processed: number;
  sources_failed: number;
  items_collected: number;
  items_failed: number;
  events_accepted: number;
  events_merged: number;
  events_reviewed: number;
  events_rejected: number;
  events_archived?: number;
}

export interface ExecutionItem {
  id: string;
  status: "RUNNING" | "COMPLETED" | "PARTIAL" | "FAILED";
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
  metrics: ExecutionMetrics;
  error_message: string | null;
}

export interface ExecutionSourceDetail {
  id: string;
  source_id: string;
  status: string;
  items_collected: number;
  items_accepted: number;
  error_message: string | null;
  duration_ms: number | null;
}

export interface ExecutionDetail extends ExecutionItem {
  sources: ExecutionSourceDetail[];
}

function adminHeaders(apiKey: string): HeadersInit {
  return { "X-Admin-Api-Key": apiKey };
}

export function fetchCycles(apiKey: string, signal?: AbortSignal): Promise<ExecutionItem[]> {
  return apiGet<ExecutionItem[]>("/api/v1/internal/cycles", signal, adminHeaders(apiKey));
}

export function fetchCycleDetail(apiKey: string, executionId: string, signal?: AbortSignal): Promise<ExecutionDetail> {
  return apiGet<ExecutionDetail>(`/api/v1/internal/cycles/${executionId}`, signal, adminHeaders(apiKey));
}

export function startCycle(apiKey: string): Promise<ExecutionItem> {
  return apiPost<ExecutionItem>("/api/v1/internal/cycles", undefined, { headers: adminHeaders(apiKey) });
}
