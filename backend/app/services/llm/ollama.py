"""Cliente Ollama para extracción estructurada."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError, LLMRateLimitedError
from app.services.llm.prompts import ANALYZER_PROMPT_VERSION, build_analyzer_prompt

logger = logging.getLogger(__name__)

# El modelo a veces envuelve la respuesta en un fence de markdown con
# identificador de lenguaje (```json ... ```). `str.strip("`")` solo saca
# los backticks y deja la palabra "json" pegada al JSON, lo que hacía
# fallar `json.loads` en la posición 0 aunque el JSON en sí fuera válido.
_CODE_FENCE_PATTERN = re.compile(r"^```[^\n`]*\n?|\n?```\s*$")

# Backoff cuando Ollama responde 429: sin esto, cada reintento inmediato
# agrava el rate limit en vez de darle margen al proveedor para recuperarse.
_RATE_LIMIT_BASE_BACKOFF_SECONDS = 2.0
_RATE_LIMIT_MAX_BACKOFF_SECONDS = 10.0


def _parse_retry_after(value: str | None) -> float | None:
    """Interpreta el header `Retry-After` cuando viene en segundos (formato usual de Ollama)."""
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


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
            "format": "json",
            "options": {"num_predict": self._max_tokens},
        }

        attempts = max(1, self._max_retries + 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started_at = time.monotonic()
            try:
                data = await self._call_ollama(payload)
            except LLMRateLimitedError as exc:
                last_error = exc
                latency_ms = (time.monotonic() - started_at) * 1000
                backoff_seconds = exc.retry_after
                if backoff_seconds is None:
                    backoff_seconds = min(
                        _RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)),
                        _RATE_LIMIT_MAX_BACKOFF_SECONDS,
                    )
                logger.warning(
                    "llm_extract_rate_limited",
                    extra={
                        "model": self._model,
                        "prompt_version": ANALYZER_PROMPT_VERSION,
                        "attempt": attempt,
                        "latency_ms": round(latency_ms, 1),
                        "backoff_seconds": backoff_seconds,
                        "error": str(exc),
                    },
                )
                if attempt < attempts:
                    await asyncio.sleep(backoff_seconds)
                continue
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
                if response.status_code == 429:
                    raise LLMRateLimitedError(
                        f"Ollama devolvió 429 (rate limit) en {self._base_url}.",
                        retry_after=_parse_retry_after(response.headers.get("retry-after")),
                    )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceNotConfiguredError(
                f"No se pudo contactar Ollama en {self._base_url}."
            ) from exc
        return response.json()

    def _parse_json_object(self, raw_output: str) -> dict[str, Any]:
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = _CODE_FENCE_PATTERN.sub("", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("La respuesta de Ollama no es JSON válido.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("La respuesta de Ollama debe ser un objeto JSON.")
        return parsed
