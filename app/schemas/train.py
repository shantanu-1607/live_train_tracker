from pydantic import BaseModel, computed_field


class TrainResponse(BaseModel):
    number: str
    name: str
    type: str
    source: str
    destination: str
    current_station: str
    delay: int

    @computed_field
    @property
    def status(self) -> str:
        if self.delay > 0:
            return f"Train is delayed by {self.delay} mins"
        elif self.delay < 0:
            return f"Train is early by {abs(self.delay)} mins"
        return "Train is on time"


class PNRResponse(BaseModel):
    pnr_number: str
    train_no: str
    doj: str
    passenger_count: int
    status_list: list[str]

    @computed_field
    @property
    def is_confirmed(self) -> bool:
        return all(s == "CNF" for s in self.status_list)


class SeatAvailabilityResponse(BaseModel):
    train_number: str
    source: str
    destination: str
    date: str
    class_code: str
    availability_status: str


class TrainScheduleResponse(BaseModel):
    train_number: str
    station_list: list[str]

    @computed_field
    @property
    def route_summary(self) -> str:
        if self.station_list:
            return f"From {self.station_list[0]} to {self.station_list[-1]}"
        return "Unknown route"

    @computed_field
    @property
    def full_schedule(self) -> str:
        return " -> ".join(self.station_list)
