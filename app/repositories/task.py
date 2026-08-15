from typing import Sequence

from app.models.project import Project
from app.models.task import Task


class TaskRepository:
    async def _get_owned_project(self, project_id: str, user_id: str) -> Project:
        return await Project.get(id=project_id, owner_id=user_id)

    async def list_for_project(self, project_id: str, user_id: str) -> Sequence[Task]:
        await self._get_owned_project(project_id, user_id)
        return await Task.filter(project_id=project_id).all()

    async def create(self, project_id: str, user_id: str, **data) -> Task:
        project = await self._get_owned_project(project_id, user_id)
        return await Task.create(project=project, **data)

    async def toggle_done(self, project_id: str, task_id: str, user_id: str) -> Task:
        project = await self._get_owned_project(project_id, user_id)
        task = await Task.get(id=task_id, project=project)
        task.done = not task.done
        await task.save()
        return task
