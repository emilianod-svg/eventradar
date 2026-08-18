import { apiGet } from "./client";
import type { EventItem, PaginatedEvents } from "../types/api";

export interface EventQuery {
  page?: number;
  pageSize?: number;
  category?: string;
  query?: string;
  dateFrom?: string;
  dateTo?: string;
}

function buildQueryString(params: EventQuery): string {
  const searchParams = new URLSearchParams();

  if (params.page !== undefined) searchParams.set("page", String(params.page));
  if (params.pageSize !== undefined) searchParams.set("page_size", String(params.pageSize));
  if (params.category) searchParams.set("category", params.category);
  if (params.query) searchParams.set("query", params.query);
  if (params.dateFrom) searchParams.set("date_from", params.dateFrom);
  if (params.dateTo) searchParams.set("date_to", params.dateTo);

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

// Consumo real de /api/v1/events. Con la base de datos vacía (estado
// inicial de esta inicialización) devuelve una lista vacía: es el
// comportamiento esperado, no un error.
export function fetchEvents(params: EventQuery = {}, signal?: AbortSignal): Promise<PaginatedEvents> {
  return apiGet<PaginatedEvents>(`/api/v1/events${buildQueryString(params)}`, signal);
}

export function fetchEvent(idOrSlug: string, signal?: AbortSignal): Promise<EventItem> {
  return apiGet<EventItem>(`/api/v1/events/${encodeURIComponent(idOrSlug)}`, signal);
}
