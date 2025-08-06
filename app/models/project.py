import uuid
from tortoise import models, fields
from app.models.user import User


class Project(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(100)
    description = fields.TextField(null=True)
    owner = fields.ForeignKeyField("models.User", related_name="projects")
    created_at = fields.DatetimeField(auto_now_add=True)
