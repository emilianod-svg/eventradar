"""Tabla `source_score_history` — evolución del aprendizaje por fuente (14.1)."""

from tortoise import fields
from tortoise.models import Model

from app.models.execution import Execution
from app.models.source import Source


class SourceScoreHistory(Model):
    id = fields.UUIDField(pk=True)
    source: fields.ForeignKeyRelation[Source] = fields.ForeignKeyField(
        "models.Source", related_name="score_history"
    )
    execution: fields.ForeignKeyNullableRelation[Execution] = fields.ForeignKeyField(
        "models.Execution", related_name="score_history", null=True
    )
    previous_score = fields.DecimalField(max_digits=4, decimal_places=3)
    new_score = fields.DecimalField(max_digits=4, decimal_places=3)
    processed_count = fields.IntField(default=0)
    accepted_count = fields.IntField(default=0)
    rejected_count = fields.IntField(default=0)
    avg_extraction_quality = fields.DecimalField(max_digits=4, decimal_places=3, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "source_score_history"
        ordering = ["-created_at"]
