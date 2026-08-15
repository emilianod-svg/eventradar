"""Repositorio de `events`."""

from __future__ import annotations

from app.domain.enums import EventStatus
from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self) -> None:
        super().__init__(Event)

    async def list_for_dedup(self) -> list[Event]:
        """Universo de eventos publicados contra el que el Evaluador busca duplicados.

        Sección 10.2 describe una selección más fina de candidatos (ventana
        de 24h, distancia, venue, similitud de título) pensada para no
        comparar contra toda la base a escala. Para el volumen actual de
        eventos de Posadas, se trae el conjunto completo de eventos
        publicados (no archivados/cancelados) y se deja que
        `RapidFuzzDuplicateMatcher` (ya implementado) haga el scoring fino;
        la pre-selección por SQL queda pendiente si el volumen lo justifica.
        """
        return await Event.filter(status__in=[EventStatus.ACTIVE, EventStatus.UPDATED])
