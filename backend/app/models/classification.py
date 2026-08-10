"""Tabla `classifications` — respuesta del analizador y evidencia (sección 9)."""

from tortoise import fields
from tortoise.models import Model


class Classification(Model):
    id = fields.UUIDField(pk=True)
    raw_content = fields.ForeignKeyField("models.RawContent", related_name="classifications")
    is_event = fields.BooleanField()
    confidence = fields.DecimalField(max_digits=4, decimal_places=3)
    extracted_fields = fields.JSONField(default=dict)
    evidence = fields.JSONField(default=dict)
    model_name = fields.CharField(max_length=100, null=True)
    prompt_version = fields.CharField(max_length=50, null=True)
    tokens_used = fields.IntField(null=True)
    latency_ms = fields.FloatField(null=True)
    cost_usd = fields.DecimalField(max_digits=8, decimal_places=4, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "classifications"
