from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import TrainTelemetry
from app.schemas.train import TrainResponse
from app.services.rail_client import RailClient

from app.db.redis_client import redis_client
CACHE_TTL_SECONDS = 60


router = APIRouter()
client = RailClient()


@router.get("/trains/{train_no}", response_model=TrainResponse)
async def get_live_status(train_no: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"train:{train_no:}"
    
    try:
        cached = await redis_client.get(cache_key)
    except Exception:
        cached = None
        
    if cached is not None:
        return TrainResponse.model_validate_json(cached)

    result = await client.get_live_status(train_no)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Train {train_no} not found")

    telemetry = TrainTelemetry(
        train_number=result.number,
        station_code=result.current_station,
        delay_minutes=result.delay,
    )
    db.add(telemetry)
    await db.commit()

    try:
        await redis_client.set(cache_key,result.model_dump_json(),ex = CACHE_TTL_SECONDS)
    except Exception:
        pass
    
    return result
