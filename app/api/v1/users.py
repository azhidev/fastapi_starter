import secrets
from hmac import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core.config import get_settings
from app.core.identifiers import RoleNamePath, XIDPath
from app.core.security import (
    AUTHENTICATE_HEADERS,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    public,
    pwd_context,
    require_active_user,
    require_roles,
)
from app.models.user import Role, User
from app.oauth.factory import require_oauth_provider
from app.oauth.service import InactiveOAuthUserError, authenticate_oauth_user
from app.oauth.types import OAuthProvider, OAuthProviderError
from app.schemas.user import RoleCreate, RoleOut, UserCreateExtra, UserOut, UserRead

settings = get_settings()
OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60


# ----- Role schemas ----------------------------------------------------------
RoleRead = pydantic_model_creator(Role, name="RoleRead")

# ----- Routers ---------------------------------------------------------------
_auth = APIRouter(prefix="/auth", tags=["auth"])
_users = APIRouter(prefix="/users", tags=["users"])
_admin = APIRouter(prefix="/admin", tags=["admin"])
_roles = APIRouter(prefix="/roles", tags=["roles"])


# ------------ Auth endpoints -------------------------------------------------
# PUBLIC: login
@_auth.post("/login")
@public
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await User.get_or_none(username=form.username)
    password_hash = (
        user.hashed_password if user is not None and user.is_active else DUMMY_PASSWORD_HASH
    )
    password_is_valid = pwd_context.verify(form.password, password_hash)

    if user is None or not user.is_active or not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers=AUTHENTICATE_HEADERS,
        )
    access = create_access_token({"sub": str(user.id)})
    return {"access_token": access, "token_type": "bearer"}


# PRIVATE: register (no decorator → private by default)
@_auth.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@public
async def register(payload: UserCreateExtra):
    hashed = pwd_context.hash(payload.password)
    user_data = payload.model_dump(exclude={"password"})
    user_data["hashed_password"] = hashed
    try:
        user = await User.create(**user_data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )
    return await UserRead.from_tortoise_orm(user)


@_auth.get("/oauth/login")
@public
async def oauth_login(provider: OAuthProvider = Depends(require_oauth_provider)):
    state_token = secrets.token_urlsafe(32)
    try:
        redirect_url = await provider.authorization_url(
            settings.oauth_redirect_uri,
            state_token,
        )
    except OAuthProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider is unavailable",
        ) from exc

    response = RedirectResponse(redirect_url)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state_token,
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/api/v1/auth/oauth",
    )
    return response


@_auth.get("/oauth/callback")
@public
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    provider: OAuthProvider = Depends(require_oauth_provider),
):
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if expected_state is None or not compare_digest(expected_state, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/api/v1/auth/oauth")

    try:
        user = await authenticate_oauth_user(provider, code, settings.oauth_redirect_uri)
    except InactiveOAuthUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        ) from exc
    except OAuthProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth authentication failed",
        ) from exc

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ------------ User admin endpoints -----------------------------------------

@_admin.get(
    "/",
    response_model=list[UserRead],
    dependencies=[Depends(require_roles("admin"))],
)
async def list_users():
    return await UserRead.from_queryset(User.all())

@_users.get("/me", response_model=UserOut)
async def get_current_user(user: User = Depends(require_active_user)):
    user = await User.get(id=user.id).prefetch_related("roles")
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[RoleOut(id=r.id, name=r.name, description=r.description) for r in user.roles],
    )


@_users.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: XIDPath, current_user: User = Depends(require_active_user)):
    if current_user.id != user_id:
        await current_user.can("admin")

    if (user := await User.get_or_none(id=user_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await UserRead.from_tortoise_orm(user)


@_users.post(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
async def assign_role(user_id: XIDPath, role_name: RoleNamePath):
    async with in_transaction() as connection:
        role = await (
            Role.filter(name=role_name)
            .using_db(connection)
            .select_for_update()
            .first()
        )
        user = await (
            User.filter(id=user_id)
            .using_db(connection)
            .select_for_update()
            .first()
        )
        if not user or not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User or role not found")
        await user.roles.add(role, using_db=connection)


@_users.delete(
    "/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
async def remove_role(user_id: XIDPath, role_name: RoleNamePath):
    async with in_transaction() as connection:
        # The role row is the stable lock shared by concurrent mutations, including
        # removals targeting different users.
        role = await (
            Role.filter(name=role_name)
            .using_db(connection)
            .select_for_update()
            .first()
        )
        user = await (
            User.filter(id=user_id)
            .using_db(connection)
            .select_for_update()
            .first()
        )
        if not user or not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User or role not found")

        has_role = await (
            User.filter(id=user.id, roles__id=role.id).using_db(connection).exists()
        )
        if role.name == "admin" and has_role:
            active_admin_count = await (
                User.filter(is_active=True, roles__id=role.id)
                .using_db(connection)
                .distinct()
                .count()
            )
            remaining_active_admins = active_admin_count - int(user.is_active)
            if remaining_active_admins < 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot remove the last active admin role",
                )

        await user.roles.remove(role, using_db=connection)


@_users.get("/{user_id}/roles", response_model=list[RoleRead])
async def list_user_roles(
    user_id: XIDPath,
    current_user: User = Depends(require_active_user),
):
    if current_user.id != user_id:
        await current_user.can("admin")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await RoleRead.from_queryset(user.roles.all())


@_roles.get(
    "/",
    response_model=list[RoleRead],
    dependencies=[Depends(require_roles("admin"))],
)
async def list_roles():
    return await RoleRead.from_queryset(Role.all())


@_roles.post(
    "/",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
async def create_role(payload: RoleCreate):
    try:
        role = await Role.create(**payload.model_dump())
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role already exists",
        ) from exc
    return await RoleRead.from_tortoise_orm(role)


@_roles.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin"))],
)
async def delete_role(role_id: XIDPath):
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    if role.name == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The admin role cannot be deleted",
        )
    await role.delete()


# ---------------------------------------------------------------------------
# Aggregate router so main.py can include just one
# ---------------------------------------------------------------------------
router = APIRouter()
router.include_router(_auth)
router.include_router(_users)
router.include_router(_roles)
router.include_router(_admin)
