"""Tabla `review_items` — casos que requieren revisión interna (sección 12.2)."""

from tortoise import fields
from tortoise.models import Model


class ReviewItem(Model):
    id = fields.UUIDField(pk=True)
    classification = fields.ForeignKeyField("models.Classification", related_name="review_items")
    status = fields.CharField(max_length=20, default="PENDING")  # PENDING|APPROVED|REJECTED
    reason = fields.TextField(null=True)
    reviewed_by = fields.CharField(max_length=100, null=True)
    reviewed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "review_items"
