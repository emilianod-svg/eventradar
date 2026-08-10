"""Tabla `raw_contents` — contenido crudo e idempotencia (sección 8.4)."""

from tortoise import fields
from tortoise.models import Model


class RawContent(Model):
    id = fields.UUIDField(pk=True)
    source = fields.ForeignKeyField("models.Source", related_name="raw_contents")
    url = fields.CharField(max_length=500)
    raw_text = fields.TextField()
    image_urls = fields.JSONField(default=list)
    published_at = fields.DatetimeField(null=True)
    fetched_at = fields.DatetimeField()
    content_hash = fields.CharField(max_length=64)
    adapter_metadata = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "raw_contents"
        unique_together = (("source", "content_hash"),)
