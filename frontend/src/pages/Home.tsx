import { useHealthCheck } from "../hooks/useHealthCheck";
import { StatusBanner } from "../components/StatusBanner";
import { EmptyState } from "../components/EmptyState";

// Pantalla inicial de EventRadar (sección 15.1 del plan). Es
// deliberadamente mínima en esta inicialización: valida la conexión con el
// backend y deja el layout base listo para agregar la grilla de cards
// cuando el flujo de recolección/análisis esté implementado.
export function Home() {
  const health = useHealthCheck();

  return (
    <main>
      <header className="app-header">
        <h1>EventRadar</h1>
        <p>Eventos en Posadas, Misiones</p>
      </header>

      <StatusBanner state={health} />

      {health.status === "ok" && (
        <EmptyState
          title="Todavía no hay eventos cargados"
          description="El backend está funcionando. Los eventos aparecerán acá cuando el primer ciclo de recolección se ejecute."
        />
      )}
    </main>
  );
}
