import { useEffect, useRef, useState } from "react";
import { useHealthCheck } from "../hooks/useHealthCheck";
import { useEvents } from "../hooks/useEvents";
import { StatusBanner } from "../components/StatusBanner";
import { EmptyState } from "../components/EmptyState";
import { EventCard } from "../components/EventCard";

export function Home() {
  const health = useHealthCheck();
  const events = useEvents();
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  const selectedEvent =
    events.status === "ready"
      ? events.items.find((event) => event.id === selectedEventId) ?? null
      : null;

  useEffect(() => {
    if (!selectedEvent) return;

    closeButtonRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedEventId(null);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedEvent]);

  return (
    <main>
      <header className="app-header">
        <h1>EventRadar</h1>
        <p>Eventos en Posadas, Misiones</p>
      </header>

      <StatusBanner state={health} />

      {health.status === "ok" && (
        <section className="events-section" aria-labelledby="events-title">
          <div className="events-section__header">
            <h2 id="events-title">Eventos</h2>
            {events.status === "ready" && (
              <p>{events.items.length} evento{events.items.length === 1 ? "" : "s"} encontrado{events.items.length === 1 ? "" : "s"}</p>
            )}
          </div>

          {events.status === "loading" && (
            <EmptyState
              title="Cargando eventos"
              description="Estamos consultando el backend para traer los eventos disponibles."
            />
          )}

          {events.status === "error" && (
            <EmptyState title="No pudimos cargar los eventos" description={events.message} />
          )}

          {events.status === "ready" && events.items.length === 0 && (
            <EmptyState
              title="Todavía no hay eventos cargados"
              description="El backend está funcionando. Los eventos aparecerán acá cuando haya registros activos."
            />
          )}

          {events.status === "ready" && events.items.length > 0 && (
            <div className="events-grid">
              {events.items.map((event) => (
                <EventCard key={event.id} event={event} onDetail={setSelectedEventId} />
              ))}
            </div>
          )}
        </section>
      )}

      {selectedEvent && (
        <div className="event-detail-backdrop" role="presentation" onClick={() => setSelectedEventId(null)}>
          <section
            className="event-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="event-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="event-detail-modal__close"
              ref={closeButtonRef}
              onClick={() => setSelectedEventId(null)}
              aria-label="Cerrar detalle"
            >
              ×
            </button>
            <p className="event-detail-modal__eyebrow">Detalle del evento</p>
            <h2 id="event-detail-title">{selectedEvent.title}</h2>
            <p className="event-detail-modal__meta">{selectedEvent.category ?? "Sin categoría"}</p>
            {selectedEvent.description && <p>{selectedEvent.description}</p>}
            <dl className="event-detail-modal__grid">
              <div>
                <dt>Fecha</dt>
                <dd>{new Date(selectedEvent.start_at).toLocaleString("es-AR")}</dd>
              </div>
              <div>
                <dt>Lugar</dt>
                <dd>{selectedEvent.venue_name}</dd>
              </div>
              {selectedEvent.address && (
                <div>
                  <dt>Dirección</dt>
                  <dd>{selectedEvent.address}</dd>
                </div>
              )}
              <div>
                <dt>Precio</dt>
                <dd>{selectedEvent.price_text ?? "Sin información"}</dd>
              </div>
              <div>
                <dt>Coordenadas</dt>
                <dd>
                  {selectedEvent.latitude !== null && selectedEvent.longitude !== null
                    ? `${selectedEvent.latitude.toFixed(4)}, ${selectedEvent.longitude.toFixed(4)}`
                    : "Sin información"}
                </dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{selectedEvent.status}</dd>
              </div>
            </dl>
            <div className="event-detail-modal__actions">
              {selectedEvent.latitude !== null && selectedEvent.longitude !== null && (
                <a
                  className="event-detail-modal__action"
                  href={`https://www.google.com/maps/search/?api=1&query=${selectedEvent.latitude},${selectedEvent.longitude}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir mapa
                </a>
              )}
              <a
                className="event-detail-modal__action event-detail-modal__action--secondary"
                href={`/api/v1/events/${selectedEvent.slug}`}
                target="_blank"
                rel="noreferrer"
              >
                Abrir detalle
              </a>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
