from tortoise.contrib.pydantic import pydantic_model_creator
from app.models.task import Task

TaskRead = pydantic_model_creator(Task, name="TaskRead", exclude=("project",))
TaskCreate = pydantic_model_creator(Task, name="TaskCreate", exclude_readonly=True, exclude=("project",))
