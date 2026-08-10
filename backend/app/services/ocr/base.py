"""Interfaz del cliente OCR (sección 9 del plan — Google Vision API)."""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError


class OCRClient(Protocol):
    async def extract_text(self, *, image_url: str) -> str: ...


class NotConfiguredOCRClient:
    async def extract_text(self, *, image_url: str) -> str:
        raise ExternalServiceNotConfiguredError(
            "OCR deshabilitado o sin credenciales de Google Vision "
            "(GOOGLE_VISION_CREDENTIALS_JSON / OCR_ENABLED=false)."
        )


def get_ocr_client() -> OCRClient:
    settings = get_settings()
    if not settings.ocr_enabled or not settings.google_vision_credentials_json:
        return NotConfiguredOCRClient()
    raise NotImplementedError(
        "Cliente de Google Vision declarado como habilitado pero sin "
        "implementación todavía."
    )
