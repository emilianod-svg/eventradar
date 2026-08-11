"""Tabla `event_change_history` — cambios y merges de eventos (sección 10.5)."""

from tortoise import fields
from tortoise.models import Model

from app.models.event import Event
from app.models.execution import Execution
from app.models.source import Source


class EventChangeHistory(Model):
    id = fields.UUIDField(pk=True)
    event: fields.ForeignKeyRelation[Event] = fields.ForeignKeyField(
        "models.Event", related_name="change_history"
    )
    field_name = fields.CharField(max_length=100)
    old_value = fields.TextField(null=True)
    new_value = fields.TextField(null=True)
    source: fields.ForeignKeyNullableRelation[Source] = fields.ForeignKeyField(
        "models.Source", related_name="event_changes", null=True
    )
    execution: fields.ForeignKeyNullableRelation[Execution] = fields.ForeignKeyField(
        "models.Execution", related_name="event_changes", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "event_change_history"
        ordering = ["-created_at"]
