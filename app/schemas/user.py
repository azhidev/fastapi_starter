from tortoise.contrib.pydantic import pydantic_model_creator
from app.models.user import User, Role

UserRead = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
UserCreate = pydantic_model_creator(User, name="UserCreate", exclude_readonly=True, exclude=("roles",))
RoleRead = pydantic_model_creator(Role, name="RoleRead")
