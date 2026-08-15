from epyxid import XID
from tortoise import fields, models


class OAuthAccount(models.Model):
    id = fields.CharField(20, pk=True, default=lambda: str(XID()))
    provider = fields.CharField(50)  # e.g. "google"
    subject = fields.CharField(255)  # provider user id
    user = fields.ForeignKeyField("models.User", related_name="oauth_accounts")

    access_token = fields.TextField()
    expires_at = fields.DatetimeField(null=True)
    refresh_token = fields.TextField(null=True)

    class Meta:
        unique_together = ("provider", "subject")
