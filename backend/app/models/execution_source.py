"""Tabla `execution_sources` — resultado individual por fuente (sección 11.1)."""

from tortoise import fields
from tortoise.models import Model


class ExecutionSource(Model):
    id = fields.UUIDField(pk=True)
    execution = fields.ForeignKeyField("models.Execution", related_name="execution_sources")
    source = fields.ForeignKeyField("models.Source", related_name="execution_sources")
    status = fields.CharField(max_length=20, default="PENDING")
    items_collected = fields.IntField(default=0)
    items_accepted = fields.IntField(default=0)
    error_message = fields.TextField(null=True)
    duration_ms = fields.FloatField(null=True)

    class Meta:
        table = "execution_sources"
        unique_together = (("execution", "source"),)
