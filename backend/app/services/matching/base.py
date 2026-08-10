"""Interfaz de matching/deduplicación (sección 10 del plan).

`rapidfuzz` ya está declarado en las dependencias del backend. La lógica de
normalización, selección de candidatos y score compuesto queda fuera de
alcance de esta inicialización.
"""

from __future__ import annotations

from typing import Protocol


class DuplicateMatcher(Protocol):
    def score(self, *, candidate: dict, existing: dict) -> float:
        """Debe implementar el score compuesto de la sección 10.3."""
        ...


class NotImplementedDuplicateMatcher:
    def score(self, *, candidate: dict, existing: dict) -> float:
        raise NotImplementedError(
            "DuplicateMatcher.score: pendiente de implementación (sección 10)."
        )


def get_duplicate_matcher() -> DuplicateMatcher:
    return NotImplementedDuplicateMatcher()
