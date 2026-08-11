"""Tabla `event_sources` — relación muchos-a-muchos evento/fuente (10.5, 11.1)."""

from tortoise import fields
from tortoise.models import Model

from app.models.event import Event
from app.models.source import Source


class EventSource(Model):
    id = fields.UUIDField(pk=True)
    event: fields.ForeignKeyRelation[Event] = fields.ForeignKeyField(
        "models.Event", related_name="event_sources"
    )
    source: fields.ForeignKeyRelation[Source] = fields.ForeignKeyField(
        "models.Source", related_name="event_sources"
    )
    source_url = fields.CharField(max_length=500)
    is_primary = fields.BooleanField(default=True)
    contributed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "event_sources"
        unique_together = (("event", "source", "source_url"),)
