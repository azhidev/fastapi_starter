from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import EmailStr, Field
from app.models.user import User, Role

UserRead = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
RoleRead = pydantic_model_creator(Role, name="RoleRead")


UserCreate = pydantic_model_creator(
    User, name="UserCreate", exclude_readonly=True, exclude=("roles", "hashed_password")
)
class UserCreateExtra(UserCreate):
    password: str = Field(..., min_length=4)
    email: EmailStr   # <-- validates email format automatically


UserCreateExtra.model_rebuild()
