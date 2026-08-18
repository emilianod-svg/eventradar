import { useEffect, useMemo, useState } from "react";
import { StatusBanner } from "../components/StatusBanner";
import { EmptyState } from "../components/EmptyState";
import { EventCard } from "../components/EventCard";
import { EventFilters } from "../components/EventFilters";
import { Pagination } from "../components/Pagination";
import { useEvents } from "../hooks/useEvents";
import { useHealthCheck } from "../hooks/useHealthCheck";

interface EventFiltersState {
  page: number;
  pageSize: number;
  query: string;
  category: string;
  dateFrom: string;
  dateTo: string;
}

const DEFAULT_FILTERS: EventFiltersState = {
  page: 1,
  pageSize: 12,
  query: "",
  category: "",
  dateFrom: "",
  dateTo: "",
};

function readFiltersFromLocation(): EventFiltersState {
  const params = new URLSearchParams(window.location.search);

  return {
    page: Math.max(1, Number(params.get("page") ?? DEFAULT_FILTERS.page) || DEFAULT_FILTERS.page),
    pageSize: Math.max(1, Number(params.get("page_size") ?? DEFAULT_FILTERS.pageSize) || DEFAULT_FILTERS.pageSize),
    query: params.get("query") ?? DEFAULT_FILTERS.query,
    category: params.get("category") ?? DEFAULT_FILTERS.category,
    dateFrom: params.get("date_from") ?? DEFAULT_FILTERS.dateFrom,
    dateTo: params.get("date_to") ?? DEFAULT_FILTERS.dateTo,
  };
}

function toIsoStart(dateInput: string): string | undefined {
  if (!dateInput) return undefined;
  return new Date(`${dateInput}T00:00:00`).toISOString();
}

function toIsoEnd(dateInput: string): string | undefined {
  if (!dateInput) return undefined;
  return new Date(`${dateInput}T23:59:59.999`).toISOString();
}

function buildLocation(filters: EventFiltersState): string {
  const params = new URLSearchParams();

  if (filters.page > 1) params.set("page", String(filters.page));
  if (filters.pageSize !== DEFAULT_FILTERS.pageSize) params.set("page_size", String(filters.pageSize));
  if (filters.query) params.set("query", filters.query);
  if (filters.category) params.set("category", filters.category);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);

  const query = params.toString();
  return query ? `?${query}` : window.location.pathname;
}

function getEventWindowDates(filters: EventFiltersState) {
  return {
    dateFrom: toIsoStart(filters.dateFrom),
    dateTo: toIsoEnd(filters.dateTo),
  };
}

export function Home() {
  const initialState = useMemo(() => readFiltersFromLocation(), []);
  const [filters, setFilters] = useState<EventFiltersState>(initialState);
  const [retryKey, setRetryKey] = useState(0);
  const eventQuery = useMemo(
    () => ({
      page: filters.page,
      pageSize: filters.pageSize,
      query: filters.query || undefined,
      category: filters.category || undefined,
      ...getEventWindowDates(filters),
    }),
    [filters]
  );

  const health = useHealthCheck(retryKey);
  const events = useEvents(eventQuery, retryKey);

  const categories = useMemo(() => {
    if (events.status !== "ready") return [];

    return Array.from(new Set(events.items.map((event) => event.category).filter(Boolean))) as string[];
  }, [events]);

  useEffect(() => {
    const onPopState = () => {
      setFilters(readFiltersFromLocation());
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const nextUrl = buildLocation(filters);
    const currentUrl = `${window.location.pathname}${window.location.search}`;

    if (nextUrl !== currentUrl) {
      window.history.replaceState(null, "", nextUrl);
    }
  }, [filters]);

  const updateFilters = (patch: Partial<EventFiltersState>) => {
    const nextFilters = {
      ...filters,
      ...patch,
      page: patch.page ?? 1,
    };
    setFilters(nextFilters);
  };

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const hasActiveFilters = Boolean(filters.query || filters.category || filters.dateFrom || filters.dateTo);
  const totalItems = events.status === "ready" ? events.total : 0;
  const featuredEventId =
    events.status === "ready" && events.items.length > 0
      ? events.items.reduce((best, current) => {
          return current.quality_score > best.quality_score ? current : best;
        }).id
      : null;

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">
          <img className="app-header__logo" src="/logo.svg" alt="EventRadar" />
          <div>
            <p className="app-header__eyebrow">EventRadar</p>
            <h1>Eventos en Posadas, Misiones</h1>
          </div>
        </div>
        <p className="app-header__lead">
          Explorá eventos activos, filtrá por categoría o fecha y abrí cada detalle con enlace compartible.
        </p>
      </header>

      <StatusBanner state={health} onRetry={() => setRetryKey((value) => value + 1)} />

      {health.status === "ok" && (
        <section className="events-section" aria-labelledby="events-title">
          <div className="events-section__header">
            <div>
              <h2 id="events-title">Eventos</h2>
              {events.status === "ready" && (
                <p>
                  {events.total} evento{events.total === 1 ? "" : "s"} encontrado{events.total === 1 ? "" : "s"}
                </p>
              )}
            </div>
            {events.status === "ready" && (
              <p className="events-section__hint">
                {filters.pageSize} por página · página {events.page} de {Math.max(1, Math.ceil(events.total / events.page_size))}
              </p>
            )}
          </div>

          <EventFilters
            query={filters.query}
            category={filters.category}
            dateFrom={filters.dateFrom}
            dateTo={filters.dateTo}
            pageSize={filters.pageSize}
            categories={categories}
            onChange={updateFilters}
            onReset={clearFilters}
          />

          {events.status === "loading" && (
            <EmptyState
              title="Cargando eventos"
              description="Estamos consultando el backend para traer los eventos disponibles."
            />
          )}

          {events.status === "error" && (
            <EmptyState
              title="No pudimos cargar los eventos"
              description={events.message}
              actionLabel="Reintentar"
              onAction={() => setRetryKey((value) => value + 1)}
            />
          )}

          {events.status === "ready" && events.items.length === 0 && (
            <EmptyState
              title={hasActiveFilters ? "No hay coincidencias" : "Todavía no hay eventos cargados"}
              description={
                hasActiveFilters
                  ? "Probá limpiar filtros o ampliar el rango de fechas para ver más resultados."
                  : "El backend está funcionando. Los eventos aparecerán acá cuando haya registros activos."
              }
              actionLabel={hasActiveFilters ? "Limpiar filtros" : undefined}
              onAction={hasActiveFilters ? clearFilters : undefined}
            />
          )}

          {events.status === "ready" && events.items.length > 0 && (
            <>
              <div className="events-grid">
                {events.status === "ready" &&
                  events.items.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    detailHref={`/events/${event.slug}`}
                    featured={event.id === featuredEventId}
                  />
                  ))}
              </div>

              <Pagination
                page={events.page}
                pageSize={events.page_size}
                total={totalItems}
                onPageChange={(page) => updateFilters({ page })}
              />
            </>
          )}
        </section>
      )}
    </main>
  );
}
