from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.exceptions import DoesNotExist

from app.core.security import require_active_user
from app.repositories.country import CountryRepository
from app.schemas.country import CountryRead

router = APIRouter(prefix="/countries", tags=["countries"])
repo = CountryRepository()


@router.get("/", response_model=list[CountryRead])
async def list_countries_with_provinces():
    qs = await repo.all_countries_with_provinces()
    return await CountryRead.from_queryset(qs)


# @router.post("/", response_model=CountryRead, status_code=status.HTTP_201_CREATED)
# async def create_task(project_id: str, payload: CountryCreate, user=Depends(require_active_user)):
#     return await repo.create(project_id, **payload.model_dump())


# @router.post("/{task_id}/toggle", response_model=CountryRead)
# async def toggle_done(project_id: str, task_id: str, user=Depends(require_active_user)):
#     try:
#         return await repo.toggle_done(task_id)
#     except DoesNotExist:
#         raise HTTPException(404, "Task not found")
