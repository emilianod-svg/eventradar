"""Logging estructurado básico y utilidades de correlación (sección 17)."""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    _correlation_id_ctx.set(value)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


# Atributos que ya forman parte del `LogRecord` estándar (o del `fmt` base):
# cualquier otra clave en `record.__dict__` viene de un `extra={...}` pasado
# explícitamente por el código de la app y debe imprimirse.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
        "correlation_id",
    }
)


class ExtraFieldsFormatter(logging.Formatter):
    """Formatter que además imprime cualquier campo pasado vía `extra=`.

    `logging.Formatter` ignora silenciosamente las claves de `extra` que no
    aparecen explícitamente en `fmt` — por eso campos como `model`,
    `attempt`, `latency_ms` o `raw_output_preview` quedaban en el
    `LogRecord` pero nunca se veían en la salida.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_ATTRS
        }
        if not extras:
            return base
        extra_str = " ".join(f"{key}={self._render(value)}" for key, value in extras.items())
        return f"{base} {extra_str}"

    @staticmethod
    def _render(value: object) -> str:
        return str(value).replace("\n", "\\n").replace("\r", "")


def configure_logging(level: str = "INFO") -> None:
    """Configura logging estructurado (texto plano con campos clave).

    Se evita una dependencia de formato JSON obligatoria para mantener la
    base simple; `python-json-logger` queda declarado en las dependencias
    por si el equipo decide adoptar salida JSON en un entorno productivo.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())
    formatter = ExtraFieldsFormatter(
        fmt=(
            "%(asctime)s level=%(levelname)s logger=%(name)s "
            "correlation_id=%(correlation_id)s message=%(message)s"
        )
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
