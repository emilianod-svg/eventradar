"""Dependencia de FastAPI para proteger las rutas `/api/v1/internal/*`.

El plan exige que las rutas internas requieran una credencial de
administración incluso sin panel gráfico (sección 12.2). En esta
inicialización se implementa el mecanismo más simple posible: un header
`X-Admin-Api-Key` comparado contra `settings.admin_api_key`.

No es rate limiting real (queda documentado como pendiente P1 en el informe
de inicialización); esto solo cubre autenticación.
"""

from __future__ import annotations

import hmac

from fastapi import Header

from app.config import get_settings
from app.domain.errors import ConfigurationError, UnauthorizedError


async def require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        raise ConfigurationError(
            "ADMIN_API_KEY no está configurada en el entorno; los endpoints "
            "internos permanecen bloqueados hasta definirla."
        )
    if not x_admin_api_key or not hmac.compare_digest(x_admin_api_key, settings.admin_api_key):
        raise UnauthorizedError("Credencial administrativa inválida o ausente.")
