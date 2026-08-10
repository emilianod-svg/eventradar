import type { HealthCheckState } from "../hooks/useHealthCheck";

interface Props {
  state: HealthCheckState;
}

// Estados obligatorios de la sección 15.4 del plan (loading/error) aplicados
// al chequeo de conexión con el backend.
export function StatusBanner({ state }: Props) {
  if (state.status === "loading") {
    return (
      <div className="status-banner status-banner--loading" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        Conectando con el backend de EventRadar…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="status-banner status-banner--error" role="alert">
        <strong>No pudimos conectar con el backend.</strong>
        <p>{state.message}</p>
      </div>
    );
  }

  return (
    <div className="status-banner status-banner--ok" role="status">
      Backend conectado correctamente.
    </div>
  );
}
