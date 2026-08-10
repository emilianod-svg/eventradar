"""Tabla `executions` — estado y métricas de cada ciclo (sección 6.3, 13)."""

from tortoise import fields
from tortoise.models import Model

from app.domain.enums import ExecutionStatus


class Execution(Model):
    id = fields.UUIDField(pk=True)
    status = fields.CharEnumField(ExecutionStatus, default=ExecutionStatus.RUNNING)
    triggered_by = fields.CharField(max_length=20, default="manual")  # manual | scheduler
    started_at = fields.DatetimeField(auto_now_add=True)
    finished_at = fields.DatetimeField(null=True)
    metrics = fields.JSONField(default=dict)
    error_message = fields.TextField(null=True)

    class Meta:
        table = "executions"
        ordering = ["-started_at"]
