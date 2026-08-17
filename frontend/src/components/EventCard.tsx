import type { EventItem } from "../types/api";

interface Props {
  event: EventItem;
  onDetail: (eventId: string) => void;
}

// Card mínima (sección 15.2 del plan). El placeholder por categoría se
// resuelve con un SVG genérico hasta definir el set final de íconos.
export function EventCard({ event, onDetail }: Props) {
  const startDate = new Date(event.start_at);
  const formattedDate = startDate.toLocaleDateString("es-AR", {
    dateStyle: "medium",
  });
  const formattedTime = startDate.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const coordinates =
    event.latitude !== null && event.longitude !== null
      ? `${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`
      : null;

  return (
    <article className="event-card">
      <img
        className="event-card__image"
        src={event.image_url ?? "/placeholders/generic.svg"}
        alt={event.category ? `Categoría: ${event.category}` : "Evento sin categoría"}
        loading="lazy"
      />
      <div className="event-card__body">
        <h3>{event.title}</h3>
        <p className="event-card__meta">{formattedDate} · {formattedTime}</p>
        <p className="event-card__meta">{event.venue_name}</p>
        {event.address && <p className="event-card__meta">{event.address}</p>}
        {event.category && <p className="event-card__tag">{event.category}</p>}
        {event.description && <p className="event-card__description">{event.description}</p>}
        <div className="event-card__footer">
          <p className="event-card__price">{event.price_text ?? "Sin información"}</p>
          {coordinates && <p className="event-card__coords">{coordinates}</p>}
        </div>
        <button
          type="button"
          className="event-card__detail-button"
          onClick={() => onDetail(event.id)}
        >
          Detalle
        </button>
      </div>
    </article>
  );
}
