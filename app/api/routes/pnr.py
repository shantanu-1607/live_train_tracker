from fastapi import APIRouter, HTTPException

from app.schemas.train import PNRResponse
from app.services.rail_client import RailClient

router = APIRouter()
client = RailClient()


@router.get("/pnr/{pnr_no}", response_model=PNRResponse)
async def get_pnr_status(pnr_no: str):
    result = await client.get_pnr_status(pnr_no)

    if result is None:
        raise HTTPException(status_code=404, detail=f"PNR {pnr_no} not found")

    return result
