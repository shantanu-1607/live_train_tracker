# 🇮🇳 Indian Rail Live Tracker

A FastAPI backend for tracking Indian Railways trains — live running status, PNR status, seat availability, and route schedules, backed by a Postgres database for telemetry history.

## Features

- 📍 **Live Status** — look up a train by number to see its current station, delay, and type (via [RailRadar](https://railradar.in)); each lookup is logged to Postgres as telemetry
- 🎫 **PNR Status** — check booking/confirmation status for a PNR
- ❤️ **Health Check** — verifies API and database connectivity

> **Note:** PNR, seat availability, and schedule lookups currently return sample/dummy data — live data for these features depends on a configured RapidAPI (IRCTC) key and is not yet fully wired up. Seat availability and schedule lookups also aren't exposed as routes yet.

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) — web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) (async) + [asyncpg](https://github.com/MagicStack/asyncpg) — Postgres access
- [Alembic](https://alembic.sqlalchemy.org/) — database migrations
- [httpx](https://www.python-httpx.org/) — async HTTP client for the RailRadar/RapidAPI APIs
- [Pydantic](https://docs.pydantic.dev/) — request/response schemas and settings

## Project Structure

```
.
├── app/
│   ├── main.py                # FastAPI app entrypoint, lifespan, router registration
│   ├── core/
│   │   └── config.py          # Settings loaded from .env (API keys, DB/Redis URLs)
│   ├── db/
│   │   ├── database.py        # Async SQLAlchemy engine/session
│   │   └── models.py          # ORM models (TrainTelemetry)
│   ├── schemas/
│   │   └── train.py           # Pydantic response models
│   ├── services/
│   │   └── rail_client.py     # RailClient — wraps calls to RailRadar / RapidAPI
│   └── api/routes/
│       ├── trains.py          # GET /trains/{train_no}
│       ├── pnr.py              # GET /pnr/{pnr_no}
│       └── health.py           # GET /health
├── alembic/                    # Database migrations
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
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/train_tracker
   REDIS_URL=redis://localhost:6379
   ```

   - `RAILRADAR_KEY` — API key from [RailRadar](https://railradar.in) (powers live train status)
   - `RAPIDAPI_KEY` — API key for the [IRCTC API on RapidAPI](https://rapidapi.com/) (powers PNR/seats/schedule once wired up). Set this to a value containing `dummy` to use sample data for PNR and seat lookups.
   - `DATABASE_URL` — async Postgres connection string
   - `REDIS_URL` — reserved for future caching use (not yet used)

3. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

4. **Run the app**

   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

## Usage

1. `GET /trains/{train_no}` — fetch a train's current location, delay, and status (e.g. `/trains/12222`). Each call is recorded in the `train_telemetry` table.
2. `GET /pnr/{pnr_no}` — check a PNR's confirmation status.
3. `GET /health` — check API and database connectivity.

## License

No license specified.
