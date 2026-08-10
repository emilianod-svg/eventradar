"""Tabla `event_sources` — relación muchos-a-muchos evento/fuente (10.5, 11.1)."""

from tortoise import fields
from tortoise.models import Model


class EventSource(Model):
    id = fields.UUIDField(pk=True)
    event = fields.ForeignKeyField("models.Event", related_name="event_sources")
    source = fields.ForeignKeyField("models.Source", related_name="event_sources")
    source_url = fields.CharField(max_length=500)
    is_primary = fields.BooleanField(default=True)
    contributed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "event_sources"
        unique_together = (("event", "source", "source_url"),)
