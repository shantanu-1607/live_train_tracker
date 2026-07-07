from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes import trains, pnr, health
from app.db.database import engine
from app.db.redis_client import redis_client
from app.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Live Train Tracker", version="1.0.0", lifespan=lifespan)

app.include_router(health.router, tags=["Health"])
app.include_router(trains.router, tags=["Trains"])
app.include_router(pnr.router, tags=["PNR"])
