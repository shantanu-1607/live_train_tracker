# 🇮🇳 Indian Rail Live Tracker

A Streamlit app for tracking Indian Railways trains in real time — live running status, PNR status, seat availability, and route schedules, all in one dashboard.

## Features

- 📍 **Live Status** — look up a train by number to see its current station, delay, and type (via [RailRadar](https://railradar.in))
- 🎫 **PNR Status** — check booking/confirmation status for a 10-digit PNR
- 💺 **Seat Availability** — check seat availability for a train/class/route/date
- 📅 **Schedule** — view a train's full route and stop list

> **Note:** PNR, seat availability, and schedule lookups currently return sample/dummy data — live data for these features depends on a configured RapidAPI (IRCTC) key and is not yet fully wired up.

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI
- [Requests](https://docs.python-requests.org/) — HTTP client for the RailRadar API
- [python-dotenv](https://pypi.org/project/python-dotenv/) — environment variable loading

## Project Structure

```
.
├── main.py     # Streamlit UI (tabs for live status, PNR, seats, schedule)
├── api.py      # RailClient — wraps calls to RailRadar / RapidAPI
├── models.py   # Train, PNR, SeatAvailability, TrainSchedule data classes
└── requirements.txt
```

## Setup

1. **Clone the repo and install dependencies**

   ```bash
   git clone <repo-url>
   cd live_train_tracker
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root:

   ```env
   RAILRADAR_KEY=your_railradar_api_key
   RAPIDAPI_KEY=your_rapidapi_key
   ```

   - `RAILRADAR_KEY` — API key from [RailRadar](https://railradar.in) (powers live train status)
   - `RAPIDAPI_KEY` — API key for the [IRCTC API on RapidAPI](https://rapidapi.com/) (powers PNR/seats/schedule once wired up). Set this to a value containing `dummy` to use sample data for PNR and seat lookups.

3. **Run the app**

   ```bash
   streamlit run main.py
   ```

   The app will open at `http://localhost:8501`.

## Usage

1. Open the **Live Status** tab and enter a train number (e.g. `12222`) to fetch its current location and delay.
2. Open the **Check PNR** tab and enter a 10-digit PNR to see its confirmation status.
3. Open the **Seats** tab to check seat availability for a class, route, and date.
4. Open the **Schedule** tab to view a train's stop-by-stop route.

## License

No license specified.
