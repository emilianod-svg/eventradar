"""Adaptador Facebook (sección 3.2 del plan — decisión abierta).

Facebook NO debe considerarse una fuente técnicamente garantizada hasta
completar una prueba real y elegir una estrategia:

1. Proveedor externo de extracción de eventos públicos.
2. Lectura de páginas administradas o autorizadas.
3. Playwright sobre contenido público, si términos y viabilidad lo permiten.
4. Fuente sustituta pública si Facebook no es estable.

No se deben sortear autenticaciones, CAPTCHAs ni restricciones técnicas de
la plataforma (regla obligatoria, sección 16.3). Este adaptador queda
deshabilitado por el flag `ENABLE_FACEBOOK_ADAPTER` hasta que el equipo
cierre la estrategia.
"""

from __future__ import annotations

from app.config import get_settings
from app.domain.entities import RawContentCandidate, SourceDefinition
from app.domain.errors import ExternalServiceNotConfiguredError


class FacebookAdapter:
    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        settings = get_settings()
        if not settings.enable_facebook_adapter:
            raise ExternalServiceNotConfiguredError(
                "El adaptador de Facebook está deshabilitado "
                "(ENABLE_FACEBOOK_ADAPTER=false) hasta definir estrategia "
                "y validarla técnica y legalmente (sección 3.2 del plan)."
            )
        raise NotImplementedError(
            "FacebookAdapter.fetch: estrategia aún no implementada aunque el "
            "flag esté activo (sección 3.2)."
        )
