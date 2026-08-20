"""Repositorio de `sources`."""

from __future__ import annotations

from app.models.source import Source
from app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self) -> None:
        super().__init__(Source)

    async def get_by_canonical_base_url(self, canonical_base_url: str) -> Source | None:
        return await Source.get_or_none(canonical_base_url=canonical_base_url)

    async def list_active(self) -> list[Source]:
        return await Source.filter(active=True)
