"""Agente Analizador (sección 8.5 y 9).

Combina texto web + OCR, llama al LLM configurado (`app/services/llm`),
valida el JSON contra el schema y aplica las reglas de confianza (>=0.70
continuar, 0.50-0.69 revisión, <0.50 rechazar).

Sección 9.2 exige permitir múltiples eventos por publicación: el LLM
devuelve `{"events": [...]}` (prompt v2) y cada elemento se procesa y
filtra de forma independiente.

Persiste una `Classification` por `raw_content` con la respuesta cruda del
LLM (sección 8.5, paso 8: "registrar modelo, versión del prompt, tokens,
latencia y costo estimado"). `LLMClient.extract_event` hoy solo devuelve el
JSON del schema de la sección 9.1, sin tokens/costo — se registran `None`
en esos campos hasta que el cliente los exponga; `model_name` y
`latency_ms` sí se pueden medir acá.
"""

from __future__ import annotations

import time
from datetime import UTC
from uuid import UUID

from app.config import get_settings
from app.domain.decisions import CONFIDENCE_ACCEPT_THRESHOLD, CONFIDENCE_REVIEW_THRESHOLD
from app.domain.entities import EventCandidate, RawContentCandidate
from app.domain.enums import ProcessingStatus
from app.models.classification import Classification
from app.services.llm.base import LLMClient, get_llm_client
from app.services.llm.prompts import ANALYZER_PROMPT_VERSION


class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or get_llm_client()

    async def execute(self, data: RawContentCandidate) -> list[EventCandidate]:
        started_at = time.monotonic()
        extracted = await self._llm_client.extract_event(
            text=data.raw_text,
            extraction_date_iso=data.fetched_at.isoformat(),
        )
        latency_ms = (time.monotonic() - started_at) * 1000

        events_list = self._extract_events_list(extracted)
        classification_id = None
        if data.id is not None:
            classification = await Classification.create(
                raw_content_id=data.id,
                is_event=any(bool(event.get("is_event")) for event in events_list),
                confidence=max(
                    (float(event.get("confidence") or 0.0) for event in events_list),
                    default=0.0,
                ),
                extracted_fields=extracted,
                model_name=get_settings().llm_model,
                prompt_version=ANALYZER_PROMPT_VERSION,
                latency_ms=latency_ms,
            )
            classification_id = classification.id

        results: list[EventCandidate] = []
        for event_dict in events_list:
            candidate = EventCandidate.model_validate(
                self._normalize_candidate(event_dict, data, classification_id)
            )

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
        classification_id: UUID | None,
    ) -> dict:
        normalized = dict(extracted)
        normalized.setdefault("description", data.raw_text)
        normalized.setdefault("title", self._extract_title(data.raw_text))
        normalized.setdefault("classification_id", classification_id)
        normalized.setdefault("source_id", data.source_id)
        normalized.setdefault("source_url", data.url)
        normalized["evidence"] = self._sanitize_evidence(normalized.get("evidence"))
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

    def _sanitize_evidence(self, value: object) -> dict[str, str]:
        """Sección 8.5, paso 6 ("validar tipos"): el LLM real a veces
        devuelve `evidence` con valores `null` para campos que no encontró
        sustento textual (en vez de omitir la clave, como pide el prompt) —
        `EventCandidate.evidence` es `dict[str, str]` estricto, así que se
        descartan las entradas no-string acá en vez de dejar que
        `model_validate` rompa el pipeline entero por un detalle cosmético.
        """
        if not isinstance(value, dict):
            return {}
        return {key: item for key, item in value.items() if isinstance(item, str)}

    def _extract_title(self, raw_text: str) -> str | None:
        first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
        return first_line or None
