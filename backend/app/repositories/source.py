"""Repositorio de `sources`."""

from __future__ import annotations

from app.models.source import Source
from app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self) -> None:
        super().__init__(Source)

    async def list_active(self) -> list[Source]:
        return await Source.filter(active=True)
