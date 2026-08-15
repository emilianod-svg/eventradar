"""Agente Orquestador (sección 8.2).

Controla el ciclo completo: lock, alta de `Execution`, fuentes activas,
pipeline Collector→Analyzer→GeoClassifier→Evaluator→Persistence por fuente
en aislamiento, aprendizaje, archivado y cierre en COMPLETED/PARTIAL/FAILED.

No implementa scraping, prompts, fuzzy matching ni SQL directo: cada paso
delega en el agente correspondiente; el Orquestador solo secuencia y
contabiliza.

Decisión de alcance (confirmada): no depende de `SourceDiscovererAgent`
(sección 8.3, todavía sin implementación ni fecha en el cronograma) — pide
las fuentes activas directas vía `SourceRepository`, sin la fórmula de
priorización de exploración/explotación. El "bono a fuente nueva" del
aprendizaje (14.2) queda sin efecto hasta que 8.3 se implemente.

`existing_events` para deduplicación se carga una sola vez al inicio del
ciclo (`EventRepository.list_for_dedup`) y se mantiene fresco durante todo
el ciclo: cada `ACCEPT`/`MERGE` persistido se registra de vuelta en el
Evaluador (`EvaluatorAgent.register_existing_event`) antes de procesar el
siguiente candidato, para que dos fuentes distintas publicando el mismo
evento en el mismo ciclo sí se detecten como duplicado entre sí (sección
10.2).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.geo_classifier import GeoClassifierAgent
from app.agents.persistence import PersistenceAgent
from app.domain.entities import AgentRunMetadata, SourceDefinition
from app.domain.enums import EvaluationDecisionType, ExecutionStatus
from app.models.execution_source import ExecutionSource
from app.models.source import Source
from app.repositories.event import EventRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.source import SourceRepository


class OrchestratorAgent:
    def __init__(
        self,
        source_repository: SourceRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
        event_repository: EventRepository | None = None,
        collector: CollectorAgent | None = None,
        analyzer: AnalyzerAgent | None = None,
        geo_classifier: GeoClassifierAgent | None = None,
        triggered_by: str = "manual",
    ) -> None:
        self._source_repository = source_repository or SourceRepository()
        self._execution_repository = execution_repository or ExecutionRepository()
        self._event_repository = event_repository or EventRepository()
        self._collector = collector or CollectorAgent()
        self._analyzer = analyzer or AnalyzerAgent()
        self._geo_classifier = geo_classifier or GeoClassifierAgent()
        self._triggered_by = triggered_by

    async def execute(self, data: None = None) -> AgentRunMetadata:
        started_at = time.monotonic()
        execution = await self._execution_repository.start_new_run(triggered_by=self._triggered_by)
        persistence = PersistenceAgent(execution_id=execution.id)
        counters = {
            "sources_processed": 0,
            "sources_failed": 0,
            "items_collected": 0,
            "events_accepted": 0,
            "events_merged": 0,
            "events_reviewed": 0,
            "events_rejected": 0,
        }

        try:
            existing_events = await self._event_repository.list_for_dedup()
            evaluator = EvaluatorAgent(existing_events=existing_events)

            sources = await self._source_repository.list_active()
            for source in sources:
                await self._process_source(
                    source=source,
                    execution_id=execution.id,
                    evaluator=evaluator,
                    persistence=persistence,
                    counters=counters,
                )

            await persistence.update_learning()
            counters["events_archived"] = await persistence.archive_past_events()

            execution.status = (
                ExecutionStatus.PARTIAL
                if counters["sources_failed"] > 0
                else ExecutionStatus.COMPLETED
            )
        except Exception as exc:  # falla estructural: no un fallo aislado de fuente
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(exc)[:2000]
        finally:
            # Libera el lock interino (migración
            # 1_20260815042852_single_running_execution.py): al dejar de
            # estar RUNNING, la unique index parcial permite una próxima
            # ejecución. TODO(17/08 - scheduler): sumar pg_advisory_lock de
            # sesión cuando entre APScheduler con múltiples workers.
            execution.finished_at = datetime.now(UTC)
            execution.metrics = counters
            await execution.save()

        return AgentRunMetadata(
            agent="OrchestratorAgent",
            duration_ms=(time.monotonic() - started_at) * 1000,
            status=execution.status,
            error_code=None if execution.status != ExecutionStatus.FAILED else "cycle_failed",
            execution_id=execution.id,
        )

    async def _process_source(
        self,
        *,
        source: Source,
        execution_id: UUID,
        evaluator: EvaluatorAgent,
        persistence: PersistenceAgent,
        counters: dict[str, int],
    ) -> None:
        source_def = SourceDefinition(
            id=source.id,
            name=source.name,
            base_url=source.base_url,
            adapter_type=source.adapter_type,
            reliability_score=float(source.reliability_score),
            active=source.active,
        )
        exec_source = await ExecutionSource.create(
            execution_id=execution_id, source=source, status="RUNNING"
        )
        items_collected = 0
        items_accepted = 0
        source_started = time.monotonic()

        try:
            raw_contents = await self._collector.execute(source_def)
            for raw_content in raw_contents:
                items_collected += 1
                candidates = await self._analyzer.execute(raw_content)
                for candidate in candidates:
                    geolocated = await self._geo_classifier.execute(candidate)
                    evaluation = await evaluator.execute(geolocated)
                    persisted_event = await persistence.execute(evaluation)
                    if persisted_event is not None:
                        # Mantiene fresco el universo de deduplicación del
                        # ciclo: sin esto, dos fuentes publicando el mismo
                        # evento nunca se detectan como duplicado entre sí
                        # (existing_events se cargó una sola vez al empezar).
                        evaluator.register_existing_event(persisted_event)
                    self._tally(evaluation.decision, counters)
                    if evaluation.decision in (
                        EvaluationDecisionType.ACCEPT,
                        EvaluationDecisionType.MERGE,
                    ):
                        items_accepted += 1
            exec_source.status = "COMPLETED"
            counters["sources_processed"] += 1
        except Exception as exc:
            # Sección 6.2/13: "un fallo no cancela las otras fuentes" — se
            # aísla acá y el ciclo sigue con la próxima fuente.
            exec_source.status = "FAILED"
            exec_source.error_message = str(exc)[:2000]
            counters["sources_failed"] += 1

        counters["items_collected"] += items_collected
        exec_source.items_collected = items_collected
        exec_source.items_accepted = items_accepted
        exec_source.duration_ms = (time.monotonic() - source_started) * 1000
        await exec_source.save()

    def _tally(self, decision: str, counters: dict[str, int]) -> None:
        counter_by_decision: dict[str, str] = {
            EvaluationDecisionType.ACCEPT: "events_accepted",
            EvaluationDecisionType.MERGE: "events_merged",
            EvaluationDecisionType.REVIEW: "events_reviewed",
            EvaluationDecisionType.REJECT: "events_rejected",
        }
        key = counter_by_decision.get(decision)
        if key is not None:
            counters[key] += 1
