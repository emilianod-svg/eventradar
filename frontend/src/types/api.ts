// Tipos mínimos del contrato de API (sección 12 del plan).
// Se amplía a medida que se implementen agentes/endpoints reales.

export interface HealthResponse {
  status: "ok";
}

export interface ReadyResponse {
  status: "ok" | "degraded";
  database: "up" | "down";
  detail?: string;
}

export interface EventItem {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  start_at: string;
  end_at: string | null;
  venue_name: string;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  price_text: string | null;
  category: string | null;
  image_url: string | null;
  status: "ACTIVE" | "UPDATED" | "CANCELLED" | "ARCHIVED";
  quality_score: number;
  source_url: string | null;
  source_name: string | null;
  source_base_url: string | null;
}

export interface PaginatedEvents {
  items: EventItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiErrorEnvelope {
  code: string;
  message: string;
  details: Record<string, unknown>;
  correlation_id: string;
}
