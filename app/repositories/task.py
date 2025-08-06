from typing import Sequence
from tortoise.exceptions import DoesNotExist

from app.models.task import Task


class TaskRepository:
    async def list_for_project(self, project_id) -> Sequence[Task]:
        return await Task.filter(project_id=project_id).all()

    async def create(self, project_id: str, **data) -> Task:
        return await Task.create(project_id=project_id, **data)

    async def toggle_done(self, task_id: str) -> Task:
        task = await Task.get(id=task_id)
        task.done = not task.done
        await task.save()
        return task
