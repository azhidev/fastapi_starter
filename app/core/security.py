from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()
ALGORITHM = "HS256"
AUTHENTICATE_HEADERS = {"WWW-Authenticate": "Bearer"}

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$AOAcwzjHuDdmrLW2du7dmw$"
    "40Wp1lORRxQVQOxYPaldvGWC1z1oAB+cB2PvFeBtHBY"
)

# IMPORTANT: auto_error=False so public routes won't 401 before our skip logic runs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(data: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    to_encode.update(
        {
            "iat": now,
            "exp": now + timedelta(seconds=settings.jwt_lifetime_seconds),
            "type": "access",
        }
    )
    return jwt.encode(to_encode, settings.secret, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


async def _user_from_token(token: str) -> "User":
    payload = verify_token(token)
    if not payload or not (user_id := payload.get("sub")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers=AUTHENTICATE_HEADERS,
        )

    user = await User.get_or_none(id=user_id)
    if not user:
        # do not leak whether the user exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers=AUTHENTICATE_HEADERS,
        )
    return user

# STRICT: raises 401 if token missing/invalid
async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> "User":
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=AUTHENTICATE_HEADERS,
        )
    return await _user_from_token(token)

async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
) -> User | None:
    if not token:
        return None
    return await _user_from_token(token)


PUBLIC_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"})


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
    maybe_user: User | None = Depends(get_current_user_optional),
) -> None:
    path = _normalize(request.url.path)
    endpoint = request.scope.get("endpoint")
    is_public = (path in PUBLIC_PATHS) or bool(getattr(endpoint, "_is_public", False))

    if maybe_user:
        request.state.user = maybe_user

    if not is_public and not maybe_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=AUTHENTICATE_HEADERS,
        )
    if not is_public and not maybe_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )


def require_active_user(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_roles(*role_names: str, all_: bool = False):
    """
    Use as: dependencies=[Depends(require_roles("admin"))]
    or with all roles required: Depends(require_roles("admin", "manager", all_=True))
    """
    async def _dep(current_user: User = Depends(require_active_user)) -> User:
        ok = await (
            User.has_all_roles if all_ else User.has_any_role
        )(current_user.id, *role_names)

        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return _dep
