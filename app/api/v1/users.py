from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from httpx_oauth.clients.google import GoogleOAuth2
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import DoesNotExist

from app.core.config import get_settings
from app.core.security import create_access_token, get_current_user, public
from app.models.user import User, Role
from app.models.oauth import OAuthAccount
from app.schemas.user import UserCreateExtra, UserRead, UserCreate

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

if settings.google_client_id and settings.google_client_secret:
    oauth_client = GoogleOAuth2(settings.google_client_id, settings.google_client_secret)

oauth_client: GoogleOAuth2 | None = None
# ----- Role schemas ----------------------------------------------------------
RoleRead = pydantic_model_creator(Role, name="RoleRead")
RoleCreate = pydantic_model_creator(Role, name="RoleCreate", exclude_readonly=True)

# ----- Routers ---------------------------------------------------------------
_auth = APIRouter(prefix="/auth", tags=["auth"])
_users = APIRouter(prefix="/users", tags=["users"])
_roles = APIRouter(prefix="/roles", tags=["roles"])


# ------------ Auth endpoints -------------------------------------------------
# PUBLIC: login
@_auth.post("/login")
@public
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await User.get_or_none(username=form.username)
    if not user or not pwd_context.verify(form.password, user.hashed_password):
        raise HTTPException(400, "Incorrect email or password")
    access = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(weeks=1))
    return {"access_token": access, "token_type": "bearer"}


# PRIVATE: register (no decorator → private by default)
@_auth.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@public
async def register(payload: UserCreateExtra):
    hashed = pwd_context.hash(payload.password)
    user_data = payload.model_dump()
    user_data["hashed_password"] = hashed
    try:
        user = await User.create(**user_data)
    except Exception as e:
        raise HTTPException(400, f"there was an error creating the user: {str(e)}")
    return await UserRead.from_tortoise_orm(user)


if oauth_client:

    @_auth.get("/google/login")
    async def google_login():
        redirect = await oauth_client.get_authorization_url(
            settings.google_redirect_uri,
            scope=("openid", "email", "profile"),
            prompt="consent",
        )
        return RedirectResponse(redirect)

    @_auth.get("/google/callback", response_model=UserRead)
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


@_users.get("/", response_model=list[UserRead])
async def list_users():
    return await UserRead.from_queryset(User.all())


@_users.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str):
    if (user := await User.get_or_none(id=user_id)) is None:
        raise HTTPException(404, "User not found")
    return await UserRead.from_tortoise_orm(user)


@_users.post("/{user_id}/roles/{role_name}", status_code=204)
async def assign_role(user_id: str, role_name: str):
    user = await User.get_or_none(id=user_id)
    role = await Role.get_or_none(name=role_name)
    if not user or not role:
        raise HTTPException(404, "User or role not found")
    await user.roles.add(role)


# ------------ Role CRUD ----------------------------------------------------


@_roles.get("/", response_model=list[RoleRead])
async def list_roles():
    return await RoleRead.from_queryset(Role.all())


@_roles.post("/", response_model=RoleRead, status_code=201)
async def create_role(payload: RoleCreate):
    role = await Role.create(**payload.model_dump())
    return await RoleRead.from_tortoise_orm(role)


@_roles.delete("/{role_id}", status_code=204)
async def delete_role(role_id: str):
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    await role.delete()


# ---------------------------------------------------------------------------
# Aggregate router so main.py can include just one
# ---------------------------------------------------------------------------
router = APIRouter()
router.include_router(_auth)
router.include_router(_users)
router.include_router(_roles)
