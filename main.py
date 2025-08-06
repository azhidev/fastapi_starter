import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from app.core.config import get_settings
from app.db.tortoise import TORTOISE_ORM, init_db
from app.api.v1 import users, projects, tasks
import uvicorn, os, logging
from dotenv import load_dotenv
from tortoise.contrib.fastapi import register_tortoise
from app.models.user import User, Role

load_dotenv()

app = FastAPI(title="FastAPI Example", version="1.0.0")
settings = get_settings()

# auth = AuthFastAPI(
#     app,
#     user_model=User,
#     role_model=Role,
#     secret_key=settings.SECRET_KEY,
#     jwt_algorithm="HS256",
# )
# auth.register_routes()


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


app.include_router(users.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


# register_tortoise(
#     app,
#     db_url=settings.database_url,
#     modules={"models": ["app.models"]},
#     generate_schemas=True,
# )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level=logging.INFO,
    )
