from tortoise.contrib.pydantic import pydantic_model_creator
from app.models.project import Project

ProjectRead = pydantic_model_creator(Project, name="ProjectRead")
ProjectCreate = pydantic_model_creator(Project, name="ProjectCreate", exclude_readonly=True, exclude=("owner",))
