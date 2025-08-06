from typing import Sequence
from tortoise.exceptions import DoesNotExist

from app.models.project import Project


class ProjectRepository:
    async def list_for_user(self, user_id) -> Sequence[Project]:
        return await Project.filter(owner_id=user_id).all()

    async def get(self, project_id: str, user_id: str) -> Project:
        return await Project.get(id=project_id, owner_id=user_id)

    async def create(self, user_id: str, **data) -> Project:
        return await Project.create(owner_id=user_id, **data)

    async def delete(self, obj: Project) -> None:
        await obj.delete()
