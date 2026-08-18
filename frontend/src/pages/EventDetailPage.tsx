import { useEventDetail } from "../hooks/useEventDetail";
import { getCategoryTheme } from "../utils/categoryTheme";
import { getEventStatusClass, getEventStatusLabel } from "../utils/eventStatus";

interface Props {
  slug: string;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("es-AR", {
    dateStyle: "full",
    timeStyle: "short",
  });
}

function buildMapEmbedUrl(latitude: number, longitude: number): string {
  const delta = 0.01;
  const left = longitude - delta;
  const right = longitude + delta;
  const top = latitude + delta;
  const bottom = latitude - delta;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${left}%2C${bottom}%2C${right}%2C${top}&layer=mapnik&marker=${latitude}%2C${longitude}`;
}

function buildFallbackInitial(value: string): string {
  const candidate = value.trim().charAt(0);
  return (candidate || "E").toUpperCase();
}

export function EventDetailPage({ slug }: Props) {
  const detail = useEventDetail(slug, null);

  return (
    <main className="detail-page">
      <div className="detail-page__shell">
        <header className="detail-page__header">
          <a className="detail-page__back" href="/">
            ← Volver al listado
          </a>
          <p className="detail-page__eyebrow">Detalle del evento</p>
          <h1>Ficha de evento</h1>
          <p className="detail-page__lead">Vista pública con diseño para compartir y leer en navegador.</p>
        </header>

        {detail.status === "loading" && (
          <section className="detail-card" aria-live="polite">
            <p className="detail-card__status">Cargando evento…</p>
            <div className="detail-skeleton" aria-hidden="true">
              <div />
              <div />
              <div />
            </div>
          </section>
        )}

        {detail.status === "error" && (
          <section className="detail-card detail-card--error" role="alert">
            <h2>No pudimos cargar el evento</h2>
            <p>{detail.message}</p>
            <div className="detail-card__actions">
              <a className="event-detail-modal__action" href="/">
                Volver al listado
              </a>
            </div>
          </section>
        )}

        {detail.status === "ready" && (
          <article className="detail-card" style={getCategoryTheme(detail.event.category)}>
            <div className="detail-card__cover">
              {detail.event.image_url ? (
                <img
                  className="detail-card__cover-image"
                  src={detail.event.image_url}
                  alt={detail.event.category ? `Cobertura de ${detail.event.category}` : detail.event.title}
                />
              ) : (
                <div className="detail-card__cover-fallback" aria-hidden="true">
                  <span className="detail-card__cover-initial">{buildFallbackInitial(detail.event.title)}</span>
                  <span className="detail-card__cover-label">{detail.event.category ?? "Evento"}</span>
                </div>
              )}
            </div>

            <div className="detail-card__hero">
              <div className="detail-card__hero-copy">
                <p className="event-detail-modal__eyebrow">{detail.event.category ?? "Sin categoría"}</p>
                <h2>{detail.event.title}</h2>
                <p className="detail-card__meta">
                  {formatDateTime(detail.event.start_at)} · {detail.event.venue_name}
                </p>
                <span className={getEventStatusClass(detail.event.status)}>{getEventStatusLabel(detail.event.status)}</span>
                {detail.event.source_url && (
                  <a className="detail-card__source-link" href={detail.event.source_url} target="_blank" rel="noreferrer">
                    Fuente original{detail.event.source_name ? ` · ${detail.event.source_name}` : ""}
                  </a>
                )}
                {detail.event.description && <p className="detail-card__copy">{detail.event.description}</p>}
              </div>
              <div className="detail-card__stat-grid">
                <div>
                  <span>Precio</span>
                  <strong>{detail.event.price_text ?? "Sin información"}</strong>
                </div>
                <div>
                  <span>Estado</span>
                  <strong>{getEventStatusLabel(detail.event.status)}</strong>
                </div>
              </div>
            </div>

            <div className="detail-card__map-block">
              <dl className="detail-card__grid">
                <div>
                  <dt>Lugar</dt>
                  <dd>{detail.event.venue_name}</dd>
                </div>
                {detail.event.address && (
                  <div>
                    <dt>Dirección</dt>
                    <dd>{detail.event.address}</dd>
                  </div>
                )}
                {detail.event.source_url && (
                  <div>
                    <dt>Fuente original</dt>
                    <dd>{detail.event.source_name ?? "Sitio de origen"}</dd>
                  </div>
                )}
              </dl>

              {detail.event.latitude !== null && detail.event.longitude !== null && (
                <section className="detail-card__map detail-card__map--prominent">
                  <div className="detail-card__map-header">
                    <h3>Mapa</h3>
                    <a
                      href={`https://www.openstreetmap.org/?mlat=${detail.event.latitude}&mlon=${detail.event.longitude}#map=15/${detail.event.latitude}/${detail.event.longitude}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Abrir en OSM
                    </a>
                  </div>
                  <iframe
                    title={`Mapa de ${detail.event.title}`}
                    src={buildMapEmbedUrl(detail.event.latitude, detail.event.longitude)}
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                </section>
              )}
            </div>

            <div className="detail-card__actions">
              {detail.event.source_url && (
                <a
                  className="event-detail-modal__action event-detail-modal__action--secondary"
                  href={detail.event.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir fuente original
                </a>
              )}
              {detail.event.latitude !== null && detail.event.longitude !== null && (
                <a
                  className="event-detail-modal__action"
                  href={`https://www.google.com/maps/search/?api=1&query=${detail.event.latitude},${detail.event.longitude}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir mapa
                </a>
              )}
              <a
                className="event-detail-modal__action event-detail-modal__action--secondary"
                href={`/api/v1/events/${detail.event.slug}`}
                target="_blank"
                rel="noreferrer"
              >
                Ver JSON
              </a>
            </div>
          </article>
        )}
      </div>
    </main>
  );
}
