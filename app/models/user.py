import uuid
from fastapi.exceptions import HTTPException
from pydantic import HttpUrl
from tortoise import fields, models
from epyxid import XID

# Simple RBAC: User ↔ Role (M2M)

class Role(models.Model):
    id = fields.CharField(20, pk=True)
    name = fields.CharField(50, unique=True)
    description = fields.TextField(null=True)

    users: fields.ManyToManyRelation["User"]

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    id = fields.CharField(20, pk=True)
    username = fields.CharField(255, unique=True, null=True, index=True)
    email = fields.CharField(255, unique=True, index=True)
    hashed_password = fields.CharField(255)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    roles: fields.ManyToManyRelation["Role"] = fields.ManyToManyField(
        "models.Role", related_name="users", through="user_role"
    )

    # ---------- Instance-level helpers ----------

    async def has_role(self, role: "Role | str") -> bool:
        name = role.name if isinstance(role, Role) else role
        return await self.roles.filter(name=name).exists()

    async def can(self, *roles: "Role | str", all_: bool = False) -> bool:
        """
        Check this user's roles.
        - roles: role instances or names
        - all_: if True, require all roles; else any one role is enough
        Raises 403 on failure (so you can just `await user.can("admin")`).
        """
        names = {r.name if isinstance(r, Role) else r for r in roles}
        if not names:
            raise HTTPException(status_code=400, detail="No role(s) provided.")

        if all_:
            count = await self.roles.filter(name__in=names).distinct().count()
            ok = count == len(names)
        else:
            ok = await self.roles.filter(name__in=names).exists()

        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True

    # ---------- Class-level helpers (no instance needed) ----------

    @classmethod
    async def has_any_role(cls, user_id: str, *role_names: str) -> bool:
        return await cls.filter(id=user_id, roles__name__in=role_names).exists()

    @classmethod
    async def has_all_roles(cls, user_id: str, *role_names: str) -> bool:
        needed = set(role_names)
        count = await Role.filter(users__id=user_id, name__in=needed).distinct().count()
        return count == len(needed)
