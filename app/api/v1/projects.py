from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from app.api.deps import current_active_user
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectRead, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])
repo = ProjectRepository()


@router.get("/", response_model=list[ProjectRead])
async def list_projects(user=Depends(current_active_user)):
    return await repo.list_for_user(user.id)


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, user=Depends(current_active_user)):
    return await repo.create(user.id, **payload.model_dump())


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, user=Depends(current_active_user)):
    try:
        return await repo.get(project_id, user.id)
    except DoesNotExist:
        raise HTTPException(404, "Project not found")


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user=Depends(current_active_user)):
    obj = await repo.get(project_id, user.id)
    await repo.delete(obj)
