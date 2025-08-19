from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import Field
from app.models.user import User, Role

UserRead = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
UserCreate = pydantic_model_creator(
    User, name="UserCreate", exclude_readonly=True, exclude=("roles", "hashed_password")
)
RoleRead = pydantic_model_creator(Role, name="RoleRead")


class UserCreateExtra(UserCreate):
    password: str = Field(..., min_length=4)


UserCreateExtra.model_rebuild()
