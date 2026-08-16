"""Normalización de ubicaciones para comparación local y geocodificación."""

from __future__ import annotations

import re
import unicodedata

_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    (r"\bav\.?\b", "avenida"),
    (r"\bpje\.?\b", "pasaje"),
    (r"\bsta\.?\b", "santa"),
    (r"\bgral\.?\b", "general"),
    (r"\bmnes\.?\b", "misiones"),
    (r"\bmis\.?\b", "misiones"),
)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_location_text(value: str | None) -> str:
    if not value:
        return ""

    text = strip_accents(value).casefold()
    text = text.replace("&", " y ")
    text = re.sub(r"[\-_/]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_query_variants(*values: str | None) -> list[str]:
    variants: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_location_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            variants.append(normalized)
    return variants
