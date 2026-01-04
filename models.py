class Train:

    def __init__(self,number,name,type,source,destination,current_station,delay):
        self.number =number
        self.name = name
        self.type = type
        self.source = source
        self.destination =destination
        self.current_station= current_station
        self.delay = delay

    def __str__(self):
        live_status = self.check_status()
        return f" [{self.number}]{self.name} | route: {self.source} -> {self.destination} | status: {live_status}"

    def check_status(self):
        ## error handelling
        try:
            delay = int(self.delay)
        except:
             return "status unknown!"

        ## logic
        if delay > 0:
            return f"train is delayed by {delay} mins"
        elif delay <0:
            return f"train is early on time by {abs(delay)} mins"
        else:
            return f"train is on time"


class PNR:

    def __init__(self,pnr_number,train_no,doj,passenger_count,status_list):
        self.pnr_number = pnr_number
        self.train_no = train_no
        self.doj = doj
        self.passenger_count = passenger_count
        self.status_list = status_list

    def __str__(self):
        return f" PNR: {self.pnr_number} | train: {self.train_no} | pass: {self.passenger_count}"

    def is_confirmed(self):
        return all(status=="CNF" for status in self.status_list)


class TrainSchedule:

    def __init__(self,train_number,station_list):
        self.train_number = train_number
        self.station_list = station_list

    def route_summary(self):
        if self.station_list:
            return f"From {self.station_list[0]} to {self.station_list[-1]}"
        return "unknow route"

    def full_schedule(self):
        return "->".join(self.station_list)


class SeatAvailability:
    def __init__(self,train_number,source,destination,date,class_code,availability_status):
        self.train_number = train_number
        self.source = source
        self.destination = destination
        self.date = date
        self.class_code = class_code
        self.availability_status = availability_status

    def __str__(self):
        return f"{self.class_code} on {self.date}: {self.availability_status}"
