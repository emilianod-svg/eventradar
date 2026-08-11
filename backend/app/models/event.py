"""Tabla `events` (sección 11.2 — campos esenciales)."""

from tortoise import fields
from tortoise.models import Model

from app.domain.enums import EventStatus


class Event(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=300)
    slug = fields.CharField(max_length=350, unique=True)
    description = fields.TextField(null=True)
    start_at = fields.DatetimeField()
    end_at = fields.DatetimeField(null=True)
    recurrence_text = fields.CharField(max_length=200, null=True)
    venue_name = fields.CharField(max_length=300)
    address = fields.CharField(max_length=500, null=True)
    latitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)
    price_text = fields.CharField(max_length=200, null=True)
    category = fields.CharField(max_length=100, null=True)
    image_url = fields.TextField(null=True)
    quality_score = fields.DecimalField(max_digits=4, decimal_places=3, default=0.0)
    status = fields.CharEnumField(EventStatus, default=EventStatus.ACTIVE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "events"
        ordering = ["start_at"]
        indexes = (("start_at",), ("status",), ("category",))

    def __str__(self) -> str:
        return f"Event({self.title})"
