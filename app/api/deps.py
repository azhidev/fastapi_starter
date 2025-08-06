from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User, Role
from app.schemas.user import UserRead


def current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_role(role_name: str):
    async def checker(user: User = Depends(current_active_user)):
        if not await user.roles.filter(name=role_name).exists():
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return Depends(checker)
