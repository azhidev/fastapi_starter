import uuid
from tortoise import models, fields
from app.models.user import User


class OAuthAccount(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    provider = fields.CharField(50)  # e.g. "google"
    subject = fields.CharField(255)  # provider user id
    user = fields.ForeignKeyField("models.User", related_name="oauth_accounts")

    access_token = fields.TextField()
    expires_at = fields.DatetimeField(null=True)
    refresh_token = fields.TextField(null=True)

    class Meta:
        unique_together = ("provider", "subject")
