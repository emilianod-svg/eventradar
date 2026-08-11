import type { EventItem } from "../types/api";

interface Props {
  event: EventItem;
}

// Card mínima (sección 15.2 del plan). El placeholder por categoría se
// resuelve con un SVG genérico hasta definir el set final de íconos.
export function EventCard({ event }: Props) {
  const formattedDate = new Date(event.start_at).toLocaleString("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  });

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
        <p className="event-card__meta">{formattedDate}</p>
        <p className="event-card__meta">{event.venue_name}</p>
        <p className="event-card__price">{event.price_text ?? "Sin información"}</p>
      </div>
    </article>
  );
}
