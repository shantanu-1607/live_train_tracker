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
