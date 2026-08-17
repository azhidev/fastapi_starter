from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from httpx_oauth.clients.google import GoogleOAuth2
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core.config import get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    public,
    pwd_context,
    require_active_user,
    require_roles,
)
from app.models.oauth import OAuthAccount
from app.models.user import Role, User
from app.schemas.user import RoleCreate, RoleOut, UserCreateExtra, UserOut, UserRead

settings = get_settings()


oauth_client: GoogleOAuth2 | None = None
if settings.google_client_id and settings.google_client_secret:
    oauth_client = GoogleOAuth2(settings.google_client_id, settings.google_client_secret)
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
            headers={"WWW-Authenticate": "Bearer"},
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


if oauth_client:

    @_auth.get("/google/login")
    @public
    async def google_login():
        redirect = await oauth_client.get_authorization_url(
            settings.google_redirect_uri,
            scope=("openid", "email", "profile"),
            prompt="consent",
        )
        return RedirectResponse(redirect)

    @_auth.get("/google/callback", response_model=UserRead)
    @public
    async def google_callback(code: str):
        token_data = await oauth_client.get_access_token(code, settings.google_redirect_uri)
        info = await oauth_client.get_id_email(token_data["access_token"])
        user = await User.get_or_none(email=info["email"])
        if not user:
            user = await User.create(email=info["email"], hashed_password="google")
        await OAuthAccount.update_or_create(
            {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
            },
            provider="google",
            subject=info["sub"],
            user=user,
        )
        return await UserRead.from_tortoise_orm(user)


# ------------ User admin endpoints -----------------------------------------

@_admin.get("/", response_model=list[UserRead],
            dependencies=[Depends(require_roles("admin"))])
async def list_users():
    return await UserRead.from_queryset(User.all())

@_users.get("/me", response_model=UserOut)
async def get_current_user(user: User = Depends(require_active_user)):
    user = await User.get(id=user.id).prefetch_related("roles")
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=[RoleOut(id=r.id, name=r.name, description=r.description) for r in user.roles]
    )


@_users.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, current_user: User = Depends(require_active_user)):
    if current_user.id != user_id:
        await current_user.can("admin")

    if (user := await User.get_or_none(id=user_id)) is None:
        raise HTTPException(404, "User not found")
    return await UserRead.from_tortoise_orm(user)


@_users.post(
    "/{user_id}/roles/{role_name}",
    status_code=204,
    dependencies=[Depends(require_roles("admin"))],
)
async def assign_role(user_id: str, role_name: str):
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
            raise HTTPException(404, "User or role not found")
        await user.roles.add(role, using_db=connection)


@_users.delete(
    "/{user_id}/roles/{role_name}",
    status_code=204,
    dependencies=[Depends(require_roles("admin"))],
)
async def remove_role(user_id: str, role_name: str):
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
            raise HTTPException(404, "User or role not found")

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
    user_id: str,
    current_user: User = Depends(require_active_user),
):
    if current_user.id != user_id:
        await current_user.can("admin")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(404, "User not found")
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
    status_code=201,
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
    status_code=204,
    dependencies=[Depends(require_roles("admin"))],
)
async def delete_role(role_id: str):
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(404, "Role not found")
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
