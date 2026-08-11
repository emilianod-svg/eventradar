import { apiGet } from "./client";
import type { PaginatedEvents } from "../types/api";

// Consumo real de /api/v1/events. Con la base de datos vacía (estado
// inicial de esta inicialización) devuelve una lista vacía: es el
// comportamiento esperado, no un error.
export function fetchEvents(signal?: AbortSignal): Promise<PaginatedEvents> {
  return apiGet<PaginatedEvents>("/api/v1/events", signal);
}
