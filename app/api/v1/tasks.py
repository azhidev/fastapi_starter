from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from app.core.security import require_active_user
from app.repositories.task import TaskRepository
from app.schemas.task import TaskRead, TaskCreate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])
repo = TaskRepository()


@router.get("/", response_model=list[TaskRead])
async def list_tasks(project_id: str, user=Depends(require_active_user)):
    return await repo.list_for_project(project_id)


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(project_id: str, payload: TaskCreate, user=Depends(require_active_user)):
    return await repo.create(project_id, **payload.model_dump())


@router.post("/{task_id}/toggle", response_model=TaskRead)
async def toggle_done(project_id: str, task_id: str, user=Depends(require_active_user)):
    try:
        return await repo.toggle_done(task_id)
    except DoesNotExist:
        raise HTTPException(404, "Task not found")
