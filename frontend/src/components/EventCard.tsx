import type { EventItem } from "../types/api";
import { getCategoryTheme } from "../utils/categoryTheme";
import { getEventStatusClass, getEventStatusLabel } from "../utils/eventStatus";

interface Props {
  event: EventItem;
  detailHref: string;
  featured?: boolean;
}

// Card mínima (sección 15.2 del plan). El placeholder por categoría se
// resuelve con un SVG genérico hasta definir el set final de íconos.
export function EventCard({ event, detailHref, featured = false }: Props) {
  const startDate = new Date(event.start_at);
  const formattedDate = startDate.toLocaleDateString("es-AR", {
    dateStyle: "medium",
  });
  const formattedTime = startDate.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const placeholderLabel = event.category ?? "Evento";
  const placeholderInitial = (event.title.trim().charAt(0) || placeholderLabel.charAt(0) || "E").toUpperCase();

  return (
    <article className={`event-card${featured ? " event-card--featured" : ""}`} style={getCategoryTheme(event.category)}>
      {event.image_url ? (
        <div className="event-card__media">
          <img
            className="event-card__image"
            src={event.image_url}
            alt={event.category ? `Categoría: ${event.category}` : "Evento sin categoría"}
            loading="lazy"
          />
          {featured && <span className="event-card__featured-chip">Destacado</span>}
        </div>
      ) : (
        <div className="event-card__placeholder" aria-hidden="true">
          {featured && <span className="event-card__featured-chip">Destacado</span>}
          <span className="event-card__placeholder-initial">{placeholderInitial}</span>
          <span className="event-card__placeholder-label">{placeholderLabel}</span>
          <span className="event-card__placeholder-subtitle">{event.venue_name}</span>
        </div>
      )}
      <div className="event-card__body">
        <div className="event-card__head">
          <div className="event-card__head-left">
            {event.category && <p className="event-card__tag">{event.category}</p>}
            <span className={getEventStatusClass(event.status)}>{getEventStatusLabel(event.status)}</span>
          </div>
          {event.source_url && (
            <a className="event-card__source" href={event.source_url} target="_blank" rel="noreferrer">
              {event.source_name ?? "Fuente original"}
            </a>
          )}
        </div>
        <h3>{event.title}</h3>
        <p className="event-card__meta">
          {formattedDate} · {formattedTime}
        </p>
        <p className="event-card__meta">{event.venue_name}</p>
        {event.address && <p className="event-card__meta">{event.address}</p>}
        {event.description && <p className="event-card__description">{event.description}</p>}
        <div className="event-card__footer">
          <p className="event-card__price">{event.price_text ?? "Sin información"}</p>
        </div>
        <div className="event-card__actions">
          <a className="event-card__detail-link" href={detailHref}>
            Ver detalle
          </a>
        </div>
      </div>
    </article>
  );
}
