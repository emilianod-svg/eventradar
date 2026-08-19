import { useEffect, useMemo, useState } from "react";
import type { ExecutionItem } from "../api/cycles";
import type { CyclesState } from "../hooks/useCycles";
import { CycleDetailModal } from "./CycleDetailModal";
import { useCycleDetail } from "../hooks/useCycleDetail";

interface CyclePanelProps {
  adminApiKey: string;
  onAdminApiKeyChange: (value: string) => void;
  state: CyclesState;
  onStartCycle: () => void;
  onRefresh: () => void;
  isStarting: boolean;
  refreshKey: number;
}

type CycleSortMode = "recent" | "failed" | "running";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function getStatusLabel(status: ExecutionItem["status"]): string {
  const labels = {
    RUNNING: "En ejecución",
    COMPLETED: "Completado",
    PARTIAL: "Parcial",
    FAILED: "Fallido",
  } as const;

  return labels[status];
}

function getStatusClass(status: ExecutionItem["status"]): string {
  return `cycle-pill cycle-pill--${status.toLowerCase()}`;
}

export function CyclePanel({
  adminApiKey,
  onAdminApiKeyChange,
  state,
  onStartCycle,
  onRefresh,
  isStarting,
  refreshKey,
}: CyclePanelProps) {
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [sortMode, setSortMode] = useState<CycleSortMode>("recent");
  const items = state.status === "ready" ? state.items : [];
  const orderedItems = useMemo(() => {
    const rankByStatus: Record<ExecutionItem["status"], number> = {
      FAILED: 0,
      PARTIAL: 1,
      RUNNING: 2,
      COMPLETED: 3,
    };

    return [...items].sort((left, right) => {
      if (sortMode === "recent") {
        return new Date(right.started_at).getTime() - new Date(left.started_at).getTime();
      }

      if (sortMode === "failed") {
        const leftRank = rankByStatus[left.status];
        const rightRank = rankByStatus[right.status];
        if (leftRank !== rightRank) return leftRank - rightRank;
        return new Date(right.started_at).getTime() - new Date(left.started_at).getTime();
      }

      if (left.status !== right.status) {
        if (left.status === "RUNNING") return -1;
        if (right.status === "RUNNING") return 1;
        if (left.status === "PARTIAL") return -1;
        if (right.status === "PARTIAL") return 1;
        if (left.status === "FAILED") return 1;
        if (right.status === "FAILED") return -1;
      }

      return new Date(right.started_at).getTime() - new Date(left.started_at).getTime();
    });
  }, [items, sortMode]);
  const selectedItem = useMemo(
    () => orderedItems.find((item) => item.id === selectedExecutionId) ?? orderedItems[0] ?? null,
    [orderedItems, selectedExecutionId]
  );
  const detailState = useCycleDetail(adminApiKey, selectedItem?.id ?? null, refreshKey);
  const runningCount = items.filter((item) => item.status === "RUNNING").length;
  const failedCount = items.filter((item) => item.status === "FAILED").length;
  const partialCount = items.filter((item) => item.status === "PARTIAL").length;
  const totalCollected = items.reduce((acc, item) => acc + Number(item.metrics.items_collected ?? 0), 0);
  const totalExcluded = items.reduce((acc, item) => acc + Number(item.metrics.items_failed ?? 0) + Number(item.metrics.events_rejected ?? 0), 0);

  useEffect(() => {
    if (!selectedExecutionId && orderedItems[0]) {
      setSelectedExecutionId(orderedItems[0].id);
      return;
    }
    if (selectedExecutionId && !orderedItems.some((item) => item.id === selectedExecutionId)) {
      setSelectedExecutionId(orderedItems[0]?.id ?? null);
    }
  }, [orderedItems, selectedExecutionId]);

  useEffect(() => {
    if (orderedItems.length > 0 && selectedExecutionId === null) {
      setSelectedExecutionId(orderedItems[0].id);
    }
  }, [orderedItems, selectedExecutionId]);

  return (
    <section className="cycles-section" aria-labelledby="cycles-title">
      <div className="cycles-section__header">
        <div>
          <h2 id="cycles-title">Ciclos</h2>
          <p>Dispará un ciclo manual y revisá el estado, métricas y errores de las últimas ejecuciones.</p>
        </div>
        <div className="cycles-section__actions">
          <button className="secondary-button" type="button" onClick={onRefresh} disabled={!adminApiKey.trim()}>
            Actualizar
          </button>
          <button className="primary-button" type="button" onClick={onStartCycle} disabled={!adminApiKey.trim() || isStarting}>
            {isStarting ? "Ejecutando..." : "Correr ciclo"}
          </button>
        </div>
      </div>

      <div className="cycles-panel">
        <label className="field cycles-panel__key">
          <span>API key admin</span>
          <input
            type="password"
            value={adminApiKey}
            onChange={(event) => onAdminApiKeyChange(event.target.value)}
            placeholder="Pegá tu X-Admin-Api-Key"
            autoComplete="off"
          />
        </label>
        <p className="cycles-panel__note">
          La clave queda solo en este navegador. Sin ella no se consultan ni disparan ciclos.
        </p>
      </div>

      <div className="cycles-summary">
        <div className="cycles-summary__item">
          <strong>{items.length}</strong>
          <span>Ejecuciones</span>
        </div>
        <div className="cycles-summary__item">
          <strong>{runningCount}</strong>
          <span>En ejecución</span>
        </div>
        <div className="cycles-summary__item">
          <strong>{failedCount + partialCount}</strong>
          <span>Con incidencias</span>
        </div>
        <div className="cycles-summary__item">
          <strong>{totalCollected}</strong>
          <span>Datos procesados</span>
        </div>
        <div className="cycles-summary__item">
          <strong>{totalExcluded}</strong>
          <span>Excluidos</span>
        </div>
      </div>

      <div className="cycles-sort" role="toolbar" aria-label="Ordenar ciclos">
        <span className="cycles-sort__label">Ordenar por</span>
        <button
          type="button"
          className={sortMode === "recent" ? "cycles-sort__button cycles-sort__button--active" : "cycles-sort__button"}
          onClick={() => setSortMode("recent")}
        >
          Más recientes
        </button>
        <button
          type="button"
          className={sortMode === "failed" ? "cycles-sort__button cycles-sort__button--active" : "cycles-sort__button"}
          onClick={() => setSortMode("failed")}
        >
          Fallidos primero
        </button>
        <button
          type="button"
          className={sortMode === "running" ? "cycles-sort__button cycles-sort__button--active" : "cycles-sort__button"}
          onClick={() => setSortMode("running")}
        >
          En ejecución primero
        </button>
      </div>

      {state.status === "missing-key" && (
        <div className="cycles-empty">
          <strong>Ingresá la clave administrativa</strong>
          <p>Necesitás `X-Admin-Api-Key` para ver y correr ciclos.</p>
        </div>
      )}

      {state.status === "loading" && (
        <div className="cycles-empty">
          <strong>Cargando ciclos</strong>
          <p>Consultando las últimas ejecuciones disponibles.</p>
        </div>
      )}

      {state.status === "error" && (
        <div className="cycles-empty cycles-empty--error">
          <strong>No pudimos cargar los ciclos</strong>
          <p>{state.message}</p>
        </div>
      )}

      {state.status === "ready" && items.length === 0 && (
        <div className="cycles-empty">
          <strong>Aún no hay ejecuciones registradas</strong>
          <p>Cuando corras el primer ciclo, va a aparecer acá con sus métricas.</p>
        </div>
      )}

      {state.status === "ready" && items.length > 0 && (
        <>
          <div className="cycles-list" role="list" aria-label="Listado de ciclos">
            {orderedItems.map((item) => {
              const isSelected = item.id === selectedItem?.id;
              const processed = Number(item.metrics.items_collected ?? 0);
              const excluded = Number(item.metrics.items_failed ?? 0) + Number(item.metrics.events_rejected ?? 0);
              const accepted = Number(item.metrics.events_accepted ?? 0) + Number(item.metrics.events_merged ?? 0);

              return (
                <button
                  key={item.id}
                  type="button"
                  className={isSelected ? "cycle-row cycle-row--selected" : "cycle-row"}
                  onClick={() => {
                    setSelectedExecutionId(item.id);
                    setIsDetailOpen(true);
                  }}
                >
                  <div className="cycle-row__main">
                    <div className="cycle-row__identity">
                      <strong>{item.id.slice(0, 8)}</strong>
                      <span className={getStatusClass(item.status)}>{getStatusLabel(item.status)}</span>
                    </div>
                    <span className="cycle-row__triggered-by">{item.triggered_by}</span>
                  </div>

                  <div className="cycle-row__details">
                    <span>{formatDateTime(item.started_at)}</span>
                    <span>{item.finished_at ? formatDateTime(item.finished_at) : "Todavía en curso"}</span>
                  </div>

                  <div className="cycle-row__metrics">
                    <span>{processed} procesados</span>
                    <span>{accepted} aceptados</span>
                    <span>{excluded} excluidos</span>
                  </div>

                  {item.error_message && <p className="cycle-row__error">{item.error_message}</p>}
                </button>
              );
            })}
          </div>
          <CycleDetailModal
            cycle={isDetailOpen && detailState.status === "ready" ? detailState.item : null}
            loading={isDetailOpen && detailState.status === "loading"}
            errorMessage={isDetailOpen && detailState.status === "error" ? detailState.message : undefined}
            onClose={() => setIsDetailOpen(false)}
          />
        </>
      )}
    </section>
  );
}
