from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=settings.jwt_lifetime_seconds))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    from app.models.user import User  # local import to avoid circular

    user = User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
