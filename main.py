import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from tortoise import Tortoise
from app.core.security import user_authentication
from app.api.middlewares import add_process_time_header
from app.core.config import get_settings
from app.db.tortoise import TORTOISE_ORM
from app.api.v1 import users, projects, tasks, calendars
import uvicorn, os, logging
from dotenv import load_dotenv
from tortoise.contrib.fastapi import register_tortoise
from app.models.user import User, Role

# Public root
from app.core.security import public  # decorator for convenience


load_dotenv()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    # await FastAPILimiter.init(App().get_redis(sync=False))
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    # await store_root_layer_information_subject_data()
    # await store_root_layer_information_content_data()

    # asyncio.run(store_root_layer_information_subject_data())
    # asyncio.run(store_root_layer_information_content_data())

    # loop.create_task(store_root_layer_information())
    # loop.create_task(store_filtered_result())

    # loop.create_task(run_schedule())
    yield
    await Tortoise.close_connections()


app = FastAPI(
    title="FastAPI Example",
    version="1.0.0",
    lifespan=lifespan,
    # Global default: private
    dependencies=[Depends(user_authentication)],
)

app.middleware("http")(add_process_time_header)


@app.get("/", tags=["public"])
@public
async def root():
    return {"ok": True}


# Feature routers (their public endpoints will be marked with @public)
app.include_router(users.router, prefix="/api/v1")
app.include_router(calendars.router, prefix="/api/v1")
# app.include_router(projects.router, prefix="/api/v1")
# app.include_router(tasks.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level=logging.INFO,
    )
