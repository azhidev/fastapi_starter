from epyxid import XID
from tortoise import fields, models


class OAuthAccount(models.Model):
    id = fields.CharField(20, pk=True, default=lambda: str(XID()))
    provider = fields.CharField(50)
    subject = fields.CharField(255)
    user = fields.ForeignKeyField("models.User", related_name="oauth_accounts")

    class Meta:
        unique_together = ("provider", "subject")
