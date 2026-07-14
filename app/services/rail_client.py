import httpx
from app.core.config import settings
from app.schemas.train import TrainResponse, PNRResponse, SeatAvailabilityResponse, TrainScheduleResponse


class RailClient:
    def __init__(self):
        self.radar_url = "https://api.railradar.in/v1"
        self.rapid_url = "https://irctc1.p.rapidapi.com/api/v1"

    async def get_live_status(self, train_no: str) -> TrainResponse | None:
        url = f"{self.radar_url}/trains/{train_no}/live"
        headers = {"Authorization": f"Bearer {settings.RAILRADAR_KEY}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return None

            data = response.json()
            train_data = data["data"]
            t_data = train_data["train"]
            curr_loc = train_data.get("currentLocation", {})

            return TrainResponse(
                number=t_data.get("number"),
                name=t_data.get("name"),
                type=t_data.get("type"),
                source=t_data.get("source", {}).get("name"),
                destination=t_data.get("destination", {}).get("name"),
                current_station=curr_loc.get("stationCode", "UNKNOWN"),
                delay=train_data.get("delayMinutes", 0),
            )
        except Exception:
            return None

    async def get_pnr_status(self, pnr_no: str) -> PNRResponse | None:
        if "dummy" in settings.RAPIDAPI_KEY:
            return PNRResponse(
                pnr_number=pnr_no,
                train_no="12301",
                doj="2026-02-20",
                passenger_count=2,
                status_list=["CNF", "CNF"],
            )
        return None

    async def get_seats(
        self, train_no: str, src: str, dest: str, date: str, cls: str
    ) -> SeatAvailabilityResponse | None:
        if "dummy" in settings.RAPIDAPI_KEY:
            return SeatAvailabilityResponse(
                train_number=train_no,
                source=src,
                destination=dest,
                date=date,
                class_code=cls,
                availability_status="AVAILABLE-42",
            )
        return None

    async def get_schedule(self, train_no: str) -> TrainScheduleResponse:
        stations = ["Howrah", "Dhanbad", "Gaya", "Prayagraj", "New Delhi"]
        return TrainScheduleResponse(train_number=train_no, station_list=stations)
