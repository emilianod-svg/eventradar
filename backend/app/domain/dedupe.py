"""Idempotencia por hash del Agente Recolector (secciones 8.4 y 13 del plan).

Filtra `RawContentCandidate` ya vistos por `content_hash`, tanto dentro de un
mismo lote (una fuente que liste el mismo ítem dos veces) como contra un
conjunto de hashes conocidos de corridas anteriores.

Alcance deliberado de esta función: solo trabaja en memoria, contra el `set`
que le pasen. No consulta ni escribe `raw_contents` en la base — ese
chequeo persistente entre ciclos queda a cargo de quien orqueste el ciclo
(Orchestrator/PersistenceAgent), que puede precargar `seen_hashes` desde la
tabla antes de llamar a esta función.
"""

from __future__ import annotations

from app.domain.entities import RawContentCandidate


def dedupe_by_hash(
    candidates: list[RawContentCandidate],
    seen_hashes: set[str] | None = None,
) -> tuple[list[RawContentCandidate], set[str]]:
    """Devuelve los candidatos con `content_hash` no visto, y el set actualizado."""

    seen = set(seen_hashes) if seen_hashes else set()
    new_candidates: list[RawContentCandidate] = []
    for candidate in candidates:
        if candidate.content_hash in seen:
            continue
        seen.add(candidate.content_hash)
        new_candidates.append(candidate)
    return new_candidates, seen
