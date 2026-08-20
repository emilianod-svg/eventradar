"""Repositorio genérico mínimo sobre modelos Tortoise.

No es un patrón completo de Unit of Work; es un envoltorio delgado para que
los agentes no dependan directamente del ORM (sección 6.2: "Dependencias
externas encapsuladas mediante adaptadores").
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from tortoise.models import Model

ModelT = TypeVar("ModelT", bound=Model)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    async def get_by_id(self, id_: UUID) -> ModelT | None:
        return await self.model.get_or_none(id=id_)

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        return await self.model.all().offset(offset).limit(limit)

    async def create(self, **kwargs) -> ModelT:
        return await self.model.create(**kwargs)
