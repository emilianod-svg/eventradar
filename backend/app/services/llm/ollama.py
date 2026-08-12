"""Cliente Ollama para extracción estructurada."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError


class OllamaLLMClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        settings = get_settings()
        if not settings.llm_base_url:
            raise ExternalServiceNotConfiguredError(
                "LLM_BASE_URL no está configurada para el proveedor Ollama."
            )
        self._base_url = settings.llm_base_url.rstrip("/")
        self._model = settings.llm_model or ""
        self._timeout = settings.llm_timeout_seconds
        self._max_tokens = settings.llm_max_tokens
        self._transport = transport

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict[str, Any]:
        prompt = self._build_prompt(text=text, extraction_date_iso=extraction_date_iso)
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": self._max_tokens},
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceNotConfiguredError(
                f"No se pudo contactar Ollama en {self._base_url}."
            ) from exc

        data = response.json()
        raw_output = data.get("response", "")
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise ValueError("Ollama no devolvió una respuesta textual válida.")

        return self._parse_json_object(raw_output)

    def _build_prompt(self, *, text: str, extraction_date_iso: str) -> str:
        return (
            "Extrae un evento en JSON estricto. "
            "Devuelve solo un objeto JSON válido sin markdown ni texto extra. "
            "Campos esperados: is_event, confidence, title, start_at, end_at, "
            "recurrence_text, venue_name, address, price_text, description, "
            "category, special_requirements, evidence. "
            f"Fecha de extracción: {extraction_date_iso}.\n\n"
            f"Texto:\n{text}"
        )

    def _parse_json_object(self, raw_output: str) -> dict[str, Any]:
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("La respuesta de Ollama no es JSON válido.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("La respuesta de Ollama debe ser un objeto JSON.")
        return parsed
