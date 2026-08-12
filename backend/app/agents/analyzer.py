"""Agente Analizador (sección 8.5 y 9).

Combina texto web + OCR, llama al LLM (familia Llama, proveedor pendiente de
decisión — ver `app/services/llm`), valida el JSON contra el schema y aplica
las reglas de confianza (>=0.70 continuar, 0.50-0.69 revisión, <0.50
rechazar).
"""

from __future__ import annotations

from datetime import UTC

from app.domain.decisions import CONFIDENCE_REVIEW_THRESHOLD
from app.domain.entities import EventCandidate, RawContentCandidate
from app.services.llm.base import LLMClient, get_llm_client


class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or get_llm_client()

    async def execute(self, data: RawContentCandidate) -> list[EventCandidate]:
        extracted = await self._llm_client.extract_event(
            text=data.raw_text,
            extraction_date_iso=data.fetched_at.isoformat(),
        )
        candidate = EventCandidate.model_validate(self._normalize_candidate(extracted, data))

        if not candidate.is_event:
            return []
        if candidate.confidence < CONFIDENCE_REVIEW_THRESHOLD:
            return []
        return [candidate]

    def _normalize_candidate(
        self,
        extracted: dict,
        data: RawContentCandidate,
    ) -> dict:
        normalized = dict(extracted)
        normalized.setdefault("description", data.raw_text)
        normalized.setdefault("title", self._extract_title(data.raw_text))
        normalized.setdefault("evidence", {})
        normalized.setdefault("is_event", False)
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("start_at", None)
        normalized.setdefault("end_at", None)
        normalized.setdefault("recurrence_text", None)
        normalized.setdefault("venue_name", None)
        normalized.setdefault("address", None)
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
