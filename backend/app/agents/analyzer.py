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

import re
import time
from datetime import UTC, datetime, timedelta
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
        extraction_anchor = data.published_at or data.fetched_at
        extracted = await self._llm_client.extract_event(
            text=data.raw_text,
            extraction_date_iso=extraction_anchor.isoformat(),
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
            normalized = self._normalize_candidate(event_dict, data, classification_id)
            normalized = self._enrich_candidate(normalized, data)
            candidate = EventCandidate.model_validate(normalized)

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
    def _enrich_candidate(
        self,
        candidate: dict,
        data: RawContentCandidate,
    ) -> dict:
        enriched = dict(candidate)
        anchor = data.published_at or data.fetched_at

        if not enriched.get("start_at"):
            inferred_start = self._infer_start_at(data.raw_text, anchor)
            if inferred_start is not None:
                enriched["start_at"] = inferred_start.isoformat()

        if not enriched.get("venue_name"):
            inferred_venue = self._infer_venue_name(data.raw_text)
            if inferred_venue:
                enriched["venue_name"] = inferred_venue

        if not enriched.get("address"):
            inferred_address = self._infer_address(data.raw_text)
            if inferred_address:
                enriched["address"] = inferred_address

        if not enriched.get("venue_name") and enriched.get("title"):
            enriched["venue_name"] = enriched["title"]

        if (
            not enriched.get("is_event")
            and enriched.get("start_at")
            and self._looks_event_like(data.raw_text)
        ):
            enriched["is_event"] = True

        return enriched

    def _infer_start_at(self, raw_text: str, anchor: datetime) -> datetime | None:
        normalized_text = self._strip_accents(raw_text.casefold())

        relative = self._infer_relative_date(normalized_text, anchor)
        if relative is not None:
            return relative

        absolute = self._infer_absolute_date(normalized_text, anchor)
        return absolute

    def _infer_relative_date(self, text: str, anchor: datetime) -> datetime | None:
        weekday_pattern = re.compile(
            r"\b(?:este|el proximo|proximo)\s+"
            r"(?P<weekday>lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b"
        )
        match = weekday_pattern.search(text)
        if match is None:
            return None

        weekday = self._weekday_number(match.group("weekday"))
        if weekday is None:
            return None

        days_ahead = (weekday - anchor.weekday()) % 7
        if days_ahead == 0 and "proximo" in match.group(0):
            days_ahead = 7

        target = anchor + timedelta(days=days_ahead)
        time_value = self._infer_time(text, start_index=match.end())
        return target.replace(
            hour=time_value[0],
            minute=time_value[1],
            second=0,
            microsecond=0,
        )

    def _infer_absolute_date(self, text: str, anchor: datetime) -> datetime | None:
        date_pattern = re.compile(
            r"\b(?P<day>\d{1,2})\s+de\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
            r"septiembre|setiembre|octubre|noviembre|diciembre)(?:\s+de\s+(?P<year>\d{4}))?\b"
        )
        match = date_pattern.search(text)
        if match is None:
            return None

        month = self._month_number(match.group("month"))
        if month is None:
            return None

        day = int(match.group("day"))
        year = int(match.group("year")) if match.group("year") else anchor.year
        try:
            target = anchor.replace(year=year, month=month, day=day)
        except ValueError:
            return None
        if not match.group("year") and target.date() < anchor.date():
            try:
                target = target.replace(year=year + 1)
            except ValueError:
                return None

        time_value = self._infer_time(text, start_index=match.end())
        return target.replace(
            hour=time_value[0],
            minute=time_value[1],
            second=0,
            microsecond=0,
        )

    def _infer_time(self, text: str, *, start_index: int = 0) -> tuple[int, int]:
        time_pattern = re.compile(r"\b(?:a las|las)\s+(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\b")
        match = time_pattern.search(text, pos=start_index)
        if match is None:
            return (0, 0)
        hour = max(0, min(23, int(match.group("hour"))))
        minute = int(match.group("minute") or 0)
        return (hour, max(0, min(59, minute)))

    def _infer_venue_name(self, raw_text: str) -> str | None:
        patterns = [
            re.compile(r"\bser[aá]\s+en\s+el\s+(?P<venue>[^,.;\n]+)", re.IGNORECASE),
            re.compile(r"\bser[aá]\s+en\s+la\s+(?P<venue>[^,.;\n]+)", re.IGNORECASE),
            re.compile(r"\bse presentara\s+en\s+el\s+(?P<venue>[^,.;\n]+)", re.IGNORECASE),
            re.compile(r"\bse presentará\s+en\s+el\s+(?P<venue>[^,.;\n]+)", re.IGNORECASE),
            re.compile(r"\bubicado en\s+(?P<venue>[^,.;\n]+)", re.IGNORECASE),
        ]
        for pattern in patterns:
            match = pattern.search(raw_text)
            if match is None:
                continue
            venue = match.group("venue").strip()
            if venue:
                return venue
        return None

    def _infer_address(self, raw_text: str) -> str | None:
        patterns = [
            re.compile(r"\bubicado en\s+(?P<address>[^.\n]+)", re.IGNORECASE),
            re.compile(r"\bdireccion:\s*(?P<address>[^.\n]+)", re.IGNORECASE),
            re.compile(r"\bdirección:\s*(?P<address>[^.\n]+)", re.IGNORECASE),
        ]
        for pattern in patterns:
            match = pattern.search(raw_text)
            if match is None:
                continue
            address = match.group("address").strip().rstrip(",")
            if address:
                return address
        return None

    def _looks_event_like(self, raw_text: str) -> bool:
        text = self._strip_accents(raw_text.casefold())
        keywords = (
            "entrada",
            "entradas",
            "funcion",
            "función",
            "presentacion",
            "presentación",
            "obra",
            "festival",
            "fiesta",
            "recital",
            "show",
            "ciclo",
            "teatro",
            "muestra",
            "taller",
        )
        return any(keyword in text for keyword in keywords)

    def _weekday_number(self, weekday: str) -> int | None:
        normalized = self._strip_accents(weekday.casefold())
        mapping = {
            "lunes": 0,
            "martes": 1,
            "miercoles": 2,
            "jueves": 3,
            "viernes": 4,
            "sabado": 5,
            "domingo": 6,
        }
        return mapping.get(normalized)

    def _month_number(self, month: str) -> int | None:
        normalized = self._strip_accents(month.casefold())
        mapping = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "setiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }
        return mapping.get(normalized)

    def _strip_accents(self, value: str) -> str:
        import unicodedata

        return "".join(
            char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
        )

    def _extract_title(self, raw_text: str) -> str | None:
        first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
        return first_line or None
