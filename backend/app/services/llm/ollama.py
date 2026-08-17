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
            "format": "json",
            "options": {"num_predict": self._max_tokens},
        }

        attempts = max(1, self._max_retries + 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started_at = time.monotonic()
            data = await self._call_ollama(payload)
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
                        "raw_output_len": len(raw_output) if isinstance(raw_output, str) else None,
                        "raw_output_preview": self._preview_output(raw_output),
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
        cleaned = self._strip_code_fences(raw_output).strip()
        candidates = [cleaned]
        brace_index = cleaned.find("{")
        if brace_index > 0:
            candidates.append(cleaned[brace_index:])

        decoder = json.JSONDecoder()
        for candidate in candidates:
            parsed = self._decode_json_object(candidate, decoder)
            if parsed is not None:
                return parsed

        raise ValueError("La respuesta de Ollama no es JSON válido.")

    def _decode_json_object(
        self,
        candidate: str,
        decoder: json.JSONDecoder,
    ) -> dict[str, Any] | None:
        try:
            parsed, _ = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            return None

        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, str):
            nested = parsed.strip()
            if nested.startswith("{"):
                try:
                    nested_parsed = json.loads(nested)
                except json.JSONDecodeError:
                    return None
                if isinstance(nested_parsed, dict):
                    return nested_parsed
        return None

    def _strip_code_fences(self, raw_output: str) -> str:
        text = raw_output.strip()
        if not text.startswith("```"):
            return text

        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        return text.strip().strip("`").strip()

    def _preview_output(self, raw_output: object, limit: int = 240) -> str:
        if not isinstance(raw_output, str):
            return repr(raw_output)[:limit]
        return raw_output.strip()[:limit]
