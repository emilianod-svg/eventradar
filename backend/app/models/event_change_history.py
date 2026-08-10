"""Tabla `event_change_history` — cambios y merges de eventos (sección 10.5)."""

from tortoise import fields
from tortoise.models import Model


class EventChangeHistory(Model):
    id = fields.UUIDField(pk=True)
    event = fields.ForeignKeyField("models.Event", related_name="change_history")
    field_name = fields.CharField(max_length=100)
    old_value = fields.TextField(null=True)
    new_value = fields.TextField(null=True)
    source = fields.ForeignKeyField(
        "models.Source", related_name="event_changes", null=True
    )
    execution = fields.ForeignKeyField(
        "models.Execution", related_name="event_changes", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "event_change_history"
        ordering = ["-created_at"]
