import { useEffect, useMemo, useRef } from "react";
import type { EventItem } from "../types/api";

interface Props {
  event: EventItem | null;
  loading: boolean;
  errorMessage?: string;
  onClose: () => void;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("es-AR", {
    dateStyle: "full",
    timeStyle: "short",
  });
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )
  );
}

export function EventDetailModal({ event, loading, errorMessage, onClose }: Props) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const modalRef = useRef<HTMLElement | null>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  const titleId = useMemo(() => "event-detail-title", []);
  const descriptionId = useMemo(() => "event-detail-description", []);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    previouslyFocusedElement.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.dataset.modalOpen = "true";
    closeButtonRef.current?.focus();

    const handleKeyDown = (keyboardEvent: KeyboardEvent) => {
      if (keyboardEvent.key === "Escape") {
        keyboardEvent.preventDefault();
        onCloseRef.current();
      }

      if (keyboardEvent.key !== "Tab" || !modalRef.current) {
        return;
      }

      const focusableElements = getFocusableElements(modalRef.current);
      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (keyboardEvent.shiftKey && document.activeElement === firstElement) {
        keyboardEvent.preventDefault();
        lastElement.focus();
      } else if (!keyboardEvent.shiftKey && document.activeElement === lastElement) {
        keyboardEvent.preventDefault();
        firstElement.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      delete document.body.dataset.modalOpen;
      previouslyFocusedElement.current?.focus();
    };
  }, []);

  const content = (() => {
    if (loading) {
      return (
        <>
          <p className="event-detail-modal__eyebrow">Detalle del evento</p>
          <h2 id={titleId}>Cargando evento</h2>
          <p id={descriptionId} className="event-detail-modal__meta">
            Estamos recuperando la información completa.
          </p>
          <div className="detail-skeleton" aria-hidden="true">
            <div />
            <div />
            <div />
          </div>
        </>
      );
    }

    if (errorMessage) {
      return (
        <>
          <p className="event-detail-modal__eyebrow">Detalle del evento</p>
          <h2 id={titleId}>No pudimos cargar el evento</h2>
          <p id={descriptionId} className="event-detail-modal__meta">
            {errorMessage}
          </p>
          <div className="event-detail-modal__actions">
            <button type="button" className="secondary-button" onClick={() => onCloseRef.current()}>
              Cerrar
            </button>
          </div>
        </>
      );
    }

    if (!event) {
      return null;
    }

    return (
      <>
        <p className="event-detail-modal__eyebrow">Detalle del evento</p>
        <h2 id={titleId}>{event.title}</h2>
        <p id={descriptionId} className="event-detail-modal__meta">
          {event.category ?? "Sin categoría"} · {formatDateTime(event.start_at)}
        </p>
        {event.description && <p className="event-detail-modal__copy">{event.description}</p>}
        <dl className="event-detail-modal__grid">
          <div>
            <dt>Lugar</dt>
            <dd>{event.venue_name}</dd>
          </div>
          {event.address && (
            <div>
              <dt>Dirección</dt>
              <dd>{event.address}</dd>
            </div>
          )}
          <div>
            <dt>Precio</dt>
            <dd>{event.price_text ?? "Sin información"}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>{event.status}</dd>
          </div>
          <div>
            <dt>Coordenadas</dt>
            <dd>
              {event.latitude !== null && event.longitude !== null
                ? `${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`
                : "Sin información"}
            </dd>
          </div>
        </dl>
        <div className="event-detail-modal__actions">
          {event.latitude !== null && event.longitude !== null && (
            <a
              className="event-detail-modal__action"
              href={`https://www.google.com/maps/search/?api=1&query=${event.latitude},${event.longitude}`}
              target="_blank"
              rel="noreferrer"
            >
              Abrir mapa
            </a>
          )}
          <a
            className="event-detail-modal__action event-detail-modal__action--secondary"
            href={`/api/v1/events/${event.slug}`}
            target="_blank"
            rel="noreferrer"
          >
            Abrir API
          </a>
          <button type="button" className="secondary-button" onClick={() => onCloseRef.current()}>
            Cerrar
          </button>
        </div>
      </>
    );
  })();

  if (!event && !loading && !errorMessage) {
    return null;
  }

  return (
    <div className="event-detail-backdrop" role="presentation" onClick={() => onCloseRef.current()}>
      <section
        className="event-detail-modal"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={(eventClick) => eventClick.stopPropagation()}
      >
        <button
          type="button"
          className="event-detail-modal__close"
          ref={closeButtonRef}
          onClick={() => onCloseRef.current()}
          aria-label="Cerrar detalle"
        >
          ×
        </button>
        {content}
      </section>
    </div>
  );
}
