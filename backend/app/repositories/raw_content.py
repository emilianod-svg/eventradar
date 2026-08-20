"""Repositorio de `raw_contents` (idempotencia por hash, sección 8.4/13)."""

from __future__ import annotations

from uuid import UUID

from app.models.raw_content import RawContent
from app.repositories.base import BaseRepository


class RawContentRepository(BaseRepository[RawContent]):
    def __init__(self) -> None:
        super().__init__(RawContent)

    async def get_by_hash(self, *, source_id: UUID, content_hash: str) -> RawContent | None:
        return await RawContent.get_or_none(source_id=source_id, content_hash=content_hash)
