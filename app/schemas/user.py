from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.user import Role, User

UserRead = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
RoleRead = pydantic_model_creator(Role, name="RoleRead")


class UserCreateExtra(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=4)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username must not be blank")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if "/" in value or any(character.isspace() for character in value):
            raise ValueError("Role name must not contain whitespace or slashes")
        return value


class RoleOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: str
    roles: List[RoleOut] = Field(default_factory=list)  # avoid mutable default

