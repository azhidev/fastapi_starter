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


async def get_current_user(token: Optional[str]) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await User.get_or_none(id=user_id)
    if not user:
        # do not leak whether the user exists
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


# Public paths that should skip auth entirely
PUBLIC_PATHS: Final[frozenset[str]] = frozenset(
    {
        # "/",
    }
)


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
    token: Optional[str] = Depends(oauth2_scheme),  # oauth2_scheme has auto_error=False (see security.py)
) -> None:
    """
    Runs for EVERY request (set at `app = FastAPI(dependencies=[Depends(user_authentication)])`).
    - Skips auth for public paths or handlers marked with @public
    - Otherwise requires a valid Bearer token
    - On success, attaches the User to request.state.user
    """
    path = _normalize(request.url.path)
    endpoint = request.scope.get("endpoint")
    is_public = (path in PUBLIC_PATHS) or bool(getattr(endpoint, "_is_public", False))

    if is_public:
        # Public route: if a token is present, we *optionally* attach the user,
        # but we don't fail if it's missing/invalid.
        return
    if token:
        try:
            user = await get_current_user(token)
            request.state.user = user
        except Exception as e:
            raise HTTPException(400, f"token is invalid: {str(e)}")

    # Private (default): token REQUIRED
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = await get_current_user(token)
    request.state.user = user


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
