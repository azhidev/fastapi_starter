import uuid
from epyxid import XID
from tortoise import models, fields
from app.models.project import Project


class Task(models.Model):
    id = fields.CharField(20, pk=True, default=lambda: str(XID()))
    title = fields.CharField(255)
    description = fields.TextField(null=True)
    done = fields.BooleanField(default=False)
    project = fields.ForeignKeyField("models.Project", related_name="tasks")
    created_at = fields.DatetimeField(auto_now_add=True)
