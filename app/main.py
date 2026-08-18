from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os

from .api import devices, gateways, job_groups, jobs, auth, files
from .models.models import Base
from .database import engine
from .queue.redis_client import redis_client
from .scheduler.scheduler import scheduler
from .config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        await redis_client.init()
    except Exception as e:
        print(f"Warning: Could not initialize Redis ({e}). Continuing without Redis queue.")
    asyncio.create_task(scheduler.start())
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.LOGS_DIR, exist_ok=True) 
    yield
    await scheduler.stop()
    try:
        await redis_client.close()
    except Exception:
        pass


app = FastAPI(
    title="IoT Testbed API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

api_routers = [
    devices.router,
    gateways.router,
    job_groups.router,
    jobs.router,
    auth.router,
    files.router
]

for router in api_routers:
    app.include_router(router, prefix=settings.API_PREFIX)
