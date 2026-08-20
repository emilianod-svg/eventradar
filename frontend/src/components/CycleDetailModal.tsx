import { useEffect, useMemo, useRef } from "react";
import type { ExecutionDetail } from "../api/cycles";

interface Props {
  cycle: ExecutionDetail | null;
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

function formatDuration(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )
  );
}

function metricValue(cycle: ExecutionDetail | null, key: keyof ExecutionDetail["metrics"]): number {
  return Number(cycle?.metrics[key] ?? 0);
}

export function CycleDetailModal({ cycle, loading, errorMessage, onClose }: Props) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const modalRef = useRef<HTMLElement | null>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  const titleId = useMemo(() => "cycle-detail-title", []);
  const descriptionId = useMemo(() => "cycle-detail-description", []);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!cycle && !loading && !errorMessage) return;

    previouslyFocusedElement.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.dataset.modalOpen = "true";
    closeButtonRef.current?.focus();

    const handleKeyDown = (keyboardEvent: KeyboardEvent) => {
      if (keyboardEvent.key === "Escape") {
        keyboardEvent.preventDefault();
        onCloseRef.current();
      }

      if (keyboardEvent.key !== "Tab" || !modalRef.current) return;

      const focusableElements = getFocusableElements(modalRef.current);
      if (focusableElements.length === 0) return;

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
  }, [cycle, errorMessage, loading]);

  const content = (() => {
    if (loading) {
      return (
        <>
          <p className="event-detail-modal__eyebrow">Detalle del ciclo</p>
          <h2 id={titleId}>Cargando ciclo</h2>
          <p id={descriptionId} className="event-detail-modal__meta">
            Estamos recuperando la ejecución seleccionada.
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
          <p className="event-detail-modal__eyebrow">Detalle del ciclo</p>
          <h2 id={titleId}>No pudimos cargar el ciclo</h2>
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

    if (!cycle) return null;

    return (
      <>
        <p className="event-detail-modal__eyebrow">Detalle del ciclo</p>
        <h2 id={titleId}>Ciclo {cycle.id.slice(0, 8)}</h2>
        <p id={descriptionId} className="event-detail-modal__meta">
          {cycle.status} · {cycle.triggered_by} · {formatDateTime(cycle.started_at)}
        </p>

        <div className="cycle-detail-modal__summary">
          <div><strong>{metricValue(cycle, "items_collected")}</strong><span>Procesados</span></div>
          <div><strong>{metricValue(cycle, "items_failed")}</strong><span>Fallidos</span></div>
          <div><strong>{metricValue(cycle, "events_accepted")}</strong><span>Aceptados</span></div>
          <div><strong>{metricValue(cycle, "events_merged")}</strong><span>Fusionados</span></div>
          <div><strong>{metricValue(cycle, "events_reviewed")}</strong><span>Revisar</span></div>
          <div><strong>{metricValue(cycle, "events_rejected")}</strong><span>Rechazados</span></div>
          <div><strong>{metricValue(cycle, "events_archived")}</strong><span>Archivados</span></div>
          <div><strong>{metricValue(cycle, "sources_processed")}/{metricValue(cycle, "sources_processed") + metricValue(cycle, "sources_failed")}</strong><span>Fuentes</span></div>
        </div>

        <dl className="cycle-detail-modal__grid">
          <div>
            <dt>Inicio</dt>
            <dd>{formatDateTime(cycle.started_at)}</dd>
          </div>
          <div>
            <dt>Fin</dt>
            <dd>{cycle.finished_at ? formatDateTime(cycle.finished_at) : "Todavía en curso"}</dd>
          </div>
          <div>
            <dt>Errores</dt>
            <dd>{cycle.error_message ?? "Sin error estructural"}</dd>
          </div>
        </dl>

        <div className="cycle-detail-modal__sources">
          <div className="cycle-detail-modal__sources-header">
            <h3>Fuentes</h3>
            <span>{cycle.sources.length}</span>
          </div>

          <div className="cycle-detail-modal__source-list">
            {cycle.sources.map((source) => (
              <article key={source.id} className="cycle-detail-modal__source-card">
                <div className="cycle-detail-modal__source-head">
                  <strong>{source.source_id.slice(0, 8)}</strong>
                  <span className={`cycle-pill cycle-pill--${source.status.toLowerCase()}`}>{source.status}</span>
                </div>
                <div className="cycle-detail-modal__source-metrics">
                  <span>{source.items_collected} procesados</span>
                  <span>{source.items_accepted} aceptados</span>
                  <span>{formatDuration(source.duration_ms)}</span>
                </div>
                {source.error_message && <p className="cycle-detail-modal__source-error">{source.error_message}</p>}
              </article>
            ))}
          </div>
        </div>

        <div className="event-detail-modal__actions">
          <button type="button" className="secondary-button" onClick={() => onCloseRef.current()}>
            Cerrar
          </button>
        </div>
      </>
    );
  })();

  if (!cycle && !loading && !errorMessage) return null;

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
