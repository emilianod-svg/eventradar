"""Tabla `evaluation_decisions` — decisión del Evaluador y scores (sección 8.7)."""

from tortoise import fields
from tortoise.models import Model

from app.domain.enums import EvaluationDecisionType
from app.models.classification import Classification
from app.models.event import Event


class EvaluationDecision(Model):
    id = fields.UUIDField(pk=True)
    classification: fields.ForeignKeyRelation[Classification] = fields.ForeignKeyField(
        "models.Classification", related_name="evaluation_decisions"
    )
    decision = fields.CharEnumField(EvaluationDecisionType)
    reasons = fields.JSONField(default=list)
    duplicate_of: fields.ForeignKeyNullableRelation[Event] = fields.ForeignKeyField(
        "models.Event", related_name="duplicate_decisions", null=True
    )
    score = fields.DecimalField(max_digits=4, decimal_places=3, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "evaluation_decisions"
