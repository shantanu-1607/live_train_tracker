import requests
from models import Train,PNR, SeatAvailability, TrainSchedule


class RailClient:
    def __init__(self,radar_key,rapid_key):
        self.radar_key =radar_key
        self.rapid_key= rapid_key
        self.radar_url ="https://api.railradar.in/api/v1"
        self.rapid_url ="https://irctc1.p.rapidapi.com/api/v1"

    def get_live_status(self, train_no):
        url = f"{self.radar_url}/trains/{train_no}"
        headers = {"X-API-Key": self.radar_key}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None

            data = response.json()
            t_data = data['data']['train']
            live_data = data['data'].get('liveData', {})
            curr_loc = live_data.get('currentLocation', {})

            return Train(
                number=t_data.get('trainNumber'),
                name=t_data.get('trainName'),
                type=t_data.get('type'),
                source=t_data.get('sourceStationName'),
                destination=t_data.get('destinationStationName'),
                current_station=curr_loc.get('stationCode', 'Station Unknown'),
                delay=live_data.get('overallDelayMinutes', 0)
            )
        except Exception:
            return None

    def get_pnr_status(self, pnr_no):
        if "dummy" in self.rapid_key:
            return PNR(
                pnr_number=pnr_no,
                train_no="12301",
                doj="2026-02-20",
                passenger_count=2,
                status_list=["CNF", "CNF"]
            )
        return None

    def get_seats(self, train_no, src, dest, date, cls):
        if "dummy" in self.rapid_key:
            return SeatAvailability(
                train_number=train_no,
                source=src,
                destination=dest,
                date=date,
                class_code=cls,
                availability_status="AVAILABLE-42"
            )
        return None

    def get_schedule(self, train_no):
        stations = ["Howrah", "Dhanbad", "Gaya", "Prayagraj", "New Delhi"]
        return TrainSchedule(train_no, stations)