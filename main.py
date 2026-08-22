from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middlewares import add_process_time_header
from app.api.v1 import users
from app.core.config import get_settings
from app.core.security import public, user_authentication
from app.db.tortoise import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    # Global default: private. Public endpoints opt out with @public.
    dependencies=[Depends(user_authentication)],
)

app.middleware("http")(add_process_time_header)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/", tags=["public"])
@public
async def root():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# Feature routers (their public endpoints are explicitly marked with @public).
app.include_router(users.router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
