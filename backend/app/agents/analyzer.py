"""Agente Analizador (sección 8.5 y 9).

Combina texto web + OCR, llama al LLM configurado (`app/services/llm`),
valida el JSON contra el schema y aplica las reglas de confianza (>=0.70
continuar, 0.50-0.69 revisión, <0.50 rechazar).

Sección 9.2 exige permitir múltiples eventos por publicación: el LLM
devuelve `{"events": [...]}` (prompt v2) y cada elemento se procesa y
filtra de forma independiente.
"""

from __future__ import annotations

from datetime import UTC

from app.domain.decisions import CONFIDENCE_ACCEPT_THRESHOLD, CONFIDENCE_REVIEW_THRESHOLD
from app.domain.entities import EventCandidate, RawContentCandidate
from app.domain.enums import ProcessingStatus
from app.services.llm.base import LLMClient, get_llm_client


class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or get_llm_client()

    async def execute(self, data: RawContentCandidate) -> list[EventCandidate]:
        extracted = await self._llm_client.extract_event(
            text=data.raw_text,
            extraction_date_iso=data.fetched_at.isoformat(),
        )

        results: list[EventCandidate] = []
        for event_dict in self._extract_events_list(extracted):
            candidate = EventCandidate.model_validate(self._normalize_candidate(event_dict, data))

            if not candidate.is_event:
                continue
            if candidate.confidence < CONFIDENCE_REVIEW_THRESHOLD:
                continue
            # Sección 9.2: "rechazar noticias sobre eventos pasados". El prompt
            # ya se lo pide al LLM, pero no es determinístico — se valida acá
            # como red de seguridad (caso obligatorio de la sección 18.3).
            if candidate.start_at is not None and candidate.start_at < data.fetched_at:
                continue
            if candidate.confidence < CONFIDENCE_ACCEPT_THRESHOLD:
                candidate = candidate.model_copy(
                    update={"processing_status": ProcessingStatus.PENDING_REVIEW}
                )
            results.append(candidate)
        return results

    def _extract_events_list(self, extracted: dict) -> list[dict]:
        events = extracted.get("events")
        if isinstance(events, list):
            return events
        if "is_event" in extracted:
            # Compatibilidad: el LLM devolvió un único objeto plano (schema
            # v1) en vez de {"events": [...]} (v2). No penalizamos al modelo
            # por no seguir el wrapper al pie de la letra.
            return [extracted]
        return []

    def _normalize_candidate(
        self,
        extracted: dict,
        data: RawContentCandidate,
    ) -> dict:
        normalized = dict(extracted)
        normalized.setdefault("description", data.raw_text)
        normalized.setdefault("title", self._extract_title(data.raw_text))
        normalized.setdefault("source_id", data.source_id)
        normalized.setdefault("source_url", data.url)
        normalized.setdefault("evidence", {})
        normalized.setdefault("is_event", False)
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("start_at", None)
        normalized.setdefault("end_at", None)
        normalized.setdefault("recurrence_text", None)
        normalized.setdefault("venue_name", None)
        normalized.setdefault("address", None)
        normalized.setdefault("latitude", None)
        normalized.setdefault("longitude", None)
        normalized.setdefault("geo_precision", None)
        normalized.setdefault("geo_query", None)
        normalized.setdefault("price_text", None)
        normalized.setdefault("category", None)
        normalized.setdefault("special_requirements", None)

        for field in ("start_at", "end_at"):
            value = normalized.get(field)
            if isinstance(value, str) and value.endswith("Z"):
                normalized[field] = value.replace("Z", "+00:00")

        if data.published_at is not None:
            normalized.setdefault("published_at", data.published_at.astimezone(UTC).isoformat())

        return normalized

    def _extract_title(self, raw_text: str) -> str | None:
        first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
        return first_line or None
