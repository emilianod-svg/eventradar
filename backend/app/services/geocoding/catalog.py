"""Catálogo local de ubicaciones frecuentes en EventRadar."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.services.geocoding.normalization import normalize_location_text


class LocationCatalogEntry(BaseModel):
    name: str
    normalized_name: str
    aliases: list[str] = Field(default_factory=list)
    city: str | None = None
    state: str | None = None
    country_code: str | None = "ar"
    latitude: float | None = None
    longitude: float | None = None
    kind: str | None = None
    allowed: bool = True


@dataclass(slots=True)
class CatalogMatch:
    entry: LocationCatalogEntry
    score: float
    matched_text: str
    exact: bool


class LocationCatalog:
    def __init__(self, entries: list[LocationCatalogEntry], version: str = "1") -> None:
        self.entries = entries
        self.version = version

    @classmethod
    def from_file(cls, path: str | Path) -> LocationCatalog:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parents[4] / file_path
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        entries = [LocationCatalogEntry.model_validate(item) for item in payload]
        return cls(entries=entries, version=file_path.stem)

    @classmethod
    def default(cls) -> LocationCatalog:
        return cls.from_file(Path("data") / "geocoding_catalog.json")

    def search(self, query: str) -> CatalogMatch | None:
        normalized_query = normalize_location_text(query)
        if not normalized_query:
            return None

        best: CatalogMatch | None = None
        for entry in self.entries:
            names = [entry.normalized_name, *entry.aliases]
            for candidate in names:
                normalized_candidate = normalize_location_text(candidate)
                if not normalized_candidate:
                    continue
                exact = normalized_candidate == normalized_query
                score = self._score(normalized_query, normalized_candidate, exact=exact)
                if best is None or score > best.score:
                    best = CatalogMatch(
                        entry=entry,
                        score=score,
                        matched_text=candidate,
                        exact=exact,
                    )
        return best

    def _score(self, left: str, right: str, *, exact: bool = False) -> float:
        if exact:
            return 1.0
        wratio = fuzz.WRatio(left, right) / 100.0
        token_set = fuzz.token_set_ratio(left, right) / 100.0
        token_sort = fuzz.token_sort_ratio(left, right) / 100.0
        return (wratio * 0.5) + (token_set * 0.3) + (token_sort * 0.2)


def load_catalog(path: str | Path | None = None) -> LocationCatalog:
    if path is None:
        return LocationCatalog.default()
    return LocationCatalog.from_file(path)
