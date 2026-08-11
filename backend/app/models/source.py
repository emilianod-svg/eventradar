"""Tabla `sources` (sección 11.1)."""

from tortoise import fields
from tortoise.models import Model


class Source(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=200)
    base_url = fields.CharField(max_length=500)
    adapter_type = fields.CharField(max_length=50)
    active = fields.BooleanField(default=True)
    reliability_score = fields.DecimalField(max_digits=4, decimal_places=3, default=0.5)
    contact_notes = fields.TextField(null=True)
    last_reviewed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "sources"
        ordering = ["-reliability_score"]

    def __str__(self) -> str:
        return f"Source({self.name})"
