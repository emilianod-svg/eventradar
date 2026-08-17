"""Cliente Ollama para extracción estructurada."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError
from app.services.llm.prompts import ANALYZER_PROMPT_VERSION, build_analyzer_prompt

logger = logging.getLogger(__name__)


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
        self._max_retries = settings.llm_max_retries
        self._transport = transport

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict[str, Any]:
        prompt = build_analyzer_prompt(text=text, extraction_date_iso=extraction_date_iso)
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": self._max_tokens},
        }

        attempts = max(1, self._max_retries + 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started_at = time.monotonic()
            try:
                data = await self._call_ollama(payload)
            except ExternalServiceNotConfiguredError as exc:
                last_error = exc
                latency_ms = (time.monotonic() - started_at) * 1000
                logger.warning(
                    "llm_extract_call_failed",
                    extra={
                        "model": self._model,
                        "prompt_version": ANALYZER_PROMPT_VERSION,
                        "attempt": attempt,
                        "latency_ms": round(latency_ms, 1),
                        "error": str(exc),
                    },
                )
                continue
            latency_ms = (time.monotonic() - started_at) * 1000
            raw_output = data.get("response", "")

            try:
                if not isinstance(raw_output, str) or not raw_output.strip():
                    raise ValueError("Ollama no devolvió una respuesta textual válida.")
                parsed = self._parse_json_object(raw_output)
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "llm_extract_invalid_json",
                    extra={
                        "model": self._model,
                        "prompt_version": ANALYZER_PROMPT_VERSION,
                        "attempt": attempt,
                        "latency_ms": round(latency_ms, 1),
                        "raw_output_preview": (
                            raw_output[:500] if isinstance(raw_output, str) else repr(raw_output)
                        ),
                    },
                )
                continue

            logger.info(
                "llm_extract_ok",
                extra={
                    "model": self._model,
                    "prompt_version": ANALYZER_PROMPT_VERSION,
                    "attempt": attempt,
                    "latency_ms": round(latency_ms, 1),
                    "eval_count": data.get("eval_count"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                },
            )
            return parsed

        assert last_error is not None
        raise last_error

    async def _call_ollama(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        return response.json()

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
