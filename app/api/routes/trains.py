from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import TrainTelemetry
from app.schemas.train import TrainResponse
from app.services.rail_client import RailClient

router = APIRouter()
client = RailClient()


@router.get("/trains/{train_no}", response_model=TrainResponse)
async def get_live_status(train_no: str, db: AsyncSession = Depends(get_db)):
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

    return result
