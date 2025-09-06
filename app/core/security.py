from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Final, Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()
ALGORITHM = "HS256"

# IMPORTANT: auto_error=False so public routes won't 401 before our skip logic runs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(seconds=settings.jwt_lifetime_seconds))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.secret, algorithms=[ALGORITHM])
    except JWTError:
        return None

async def _user_from_token(token: str) -> "User":
    payload = verify_token(token)
    if not payload or not (user_id := payload.get("sub")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await User.get_or_none(id=user_id)
    if not user:
        # do not leak whether the user exists
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user

# STRICT: raises 401 if token missing/invalid
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> "User":
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await _user_from_token(token)

# OPTIONAL: returns None if token missing/invalid (useful for public routes / global guard)
async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional["User"]:
    if not token:
        return None
    try:
        return await _user_from_token(token)
    except HTTPException:
        return None

PUBLIC_PATHS = {"/docs", "/openapi.json"}  # your list

# Public paths that should skip auth entirely
# PUBLIC_PATHS: Final[frozenset[str]] = frozenset(
#     {
#         # "/",
#     }
# )


def _normalize(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


# ---- Public marker ---------------------------------------------------------
# Use as a decorator: @public above any path operation that should be public
def public(func: Callable[..., Any]) -> Callable[..., Any]:
    setattr(func, "_is_public", True)
    return func


# ---- Global dependency -----------------------------------------------------
async def user_authentication(
    request: Request,
    maybe_user: Optional["User"] = Depends(get_current_user_optional),
) -> None:
    path = _normalize(request.url.path)
    endpoint = request.scope.get("endpoint")
    is_public = (path in PUBLIC_PATHS) or bool(getattr(endpoint, "_is_public", False))

    # attach user if present
    if maybe_user:
        request.state.user = maybe_user

    # if private, a valid user is required
    if not is_public and not maybe_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def can(role_name: str):
    async def checker(user: User = Depends(require_active_user)):
        if not await user.roles.filter(name=role_name).exists():
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return Depends(checker)


def require_active_user(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_roles(*role_names: str, all_: bool = False):
    """
    Use as: dependencies=[Depends(require_roles("admin"))]
    or with all roles required: Depends(require_roles("admin", "manager", all_=True))
    """
    async def _dep(current_user: User = Depends(get_current_user)) -> User:
        ok = await (
            User.has_all_roles if all_ else User.has_any_role
        )(current_user.id, *role_names)

        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return _dep
