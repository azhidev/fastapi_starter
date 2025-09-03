from typing import List, Optional
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import BaseModel, EmailStr, Field
from app.models.user import User, Role

UserRead = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
RoleRead = pydantic_model_creator(Role, name="RoleRead")


UserCreate = pydantic_model_creator(
    User, name="UserCreate", exclude_readonly=True, exclude=("roles", "hashed_password")
)
class UserCreateExtra(UserCreate):
    password: str = Field(..., min_length=4)
    email: EmailStr   # <-- validates email format automatically


class RoleOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: str
    roles: List[RoleOut] = Field(default_factory=list)  # avoid mutable default

UserCreateExtra.model_rebuild()
