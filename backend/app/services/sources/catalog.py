"""Catálogo declarativo de fuentes iniciales."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from app.services.sources.normalization import normalize_adapter_type, normalize_source_url


class SourceCatalogEntry(BaseModel):
    name: str
    base_url: str
    adapter_type: str
    active: bool = True
    reliability_score: float = Field(ge=0.0, le=1.0)
    notes: str | None = None

    def normalized_base_url(self) -> str | None:
        return normalize_source_url(self.base_url)

    def normalized_adapter_type(self) -> str:
        return normalize_adapter_type(self.adapter_type)


@dataclass(slots=True)
class SourceCatalog:
    entries: list[SourceCatalogEntry]
    version: str = "1"

    @classmethod
    def from_file(cls, path: str | Path) -> SourceCatalog:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parents[4] / file_path
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("El catálogo de fuentes debe ser una lista")
        entries = [
            SourceCatalogEntry.model_validate(item) for item in payload if isinstance(item, dict)
        ]
        return cls(entries=entries, version=file_path.stem)

    @classmethod
    def default(cls) -> SourceCatalog:
        return cls.from_file(Path("data") / "source_catalog.json")


def load_source_catalog(path: str | Path | None = None) -> SourceCatalog:
    if path is None:
        return SourceCatalog.default()
    return SourceCatalog.from_file(path)
