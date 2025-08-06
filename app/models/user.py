import uuid
from tortoise import fields, models

# Simple RBAC: User ↔ Role (M2M)


class Role(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(50, unique=True)
    description = fields.TextField(null=True)

    users: fields.ManyToManyRelation["User"]

    def __str__(self):
        return self.name


class User(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    email = fields.CharField(255, unique=True, index=True)
    hashed_password = fields.CharField(255)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    roles: fields.ManyToManyRelation[Role] = fields.ManyToManyField("models.Role", related_name="users", through="user_role")

    def __str__(self):
        return self.email
