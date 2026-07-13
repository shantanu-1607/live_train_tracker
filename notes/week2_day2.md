# Week 2, Day 2 — Redis Cache-Aside

**Goal for the day:** put a Redis cache-aside layer in front of the external RailRadar API call in `GET /trains/{train_no}`, so repeated lookups of the same train within a short window are served from Redis instead of hammering the (slow, rate-limited) upstream API.

**Definition of done:** two back-to-back requests for the same train within the TTL window result in exactly ONE RailRadar call + ONE telemetry row (the first, a miss); the second is served from Redis (a hit) with a byte-identical response and no new DB write.

---

## Concepts I had to know (MUST KNOW)

### 1. The cache-aside pattern

The **application code itself** is responsible for checking the cache first, and only going to the real source on a miss. The cache sits *aside* the real data source, not in its write path.

Sequence, applied to `get_live_status`:
1. Build a cache key (`train:{train_no}`) and `GET` it from Redis.
2. **Hit** → deserialize the cached JSON into a `TrainResponse` and return immediately — skip the RailRadar call *and* the Postgres telemetry write (nothing new was fetched).
3. **Miss** → call RailRadar (existing logic), write telemetry, then `SET` the result into Redis with a TTL, then return.

**Why cache-aside fits here (vs. write-through):** write-through updates the cache at the moment data is *written*. But this app never *writes* train-position data — it only ever *reads* it from RailRadar on a user's request. There's no natural write moment to populate the cache proactively (yet — Day 3's Celery Beat polling will become exactly that kind of proactive writer). The only trigger available now is "a user asked," so the cache must be populated lazily, on a miss. That *is* cache-aside.

### 2. TTL (Time To Live)

TTL is a countdown attached to a cached entry when it's stored ("auto-forget this after N seconds"). In Redis: `SET key value EX 60` / `SETEX`. When it elapses, Redis deletes the key itself; the next lookup is a miss, forcing a fresh fetch + repopulate.

**Chosen value: 60 seconds.** Reasoning:
- TTL should roughly match how fast the underlying real-world data actually changes. Caching *longer* than that serves stale-but-confident data (bad for a "live" tracker); caching *much shorter* than the source's own refresh cadence gains little.
- RailRadar's upstream (NTES) refreshes on the order of a few minutes, and a train changes station every ~10–40 min. 60s is short enough to still feel live, long enough to meaningfully cut repeated calls when a train is polled frequently.
- It's an **approximation, tuned by feel/data — not a precise offset**. You don't know the exact upstream cadence, and you can't align your TTL start to the upstream refresh anyway. Pick a sensible round number now; later validate/adjust against real cache-hit-rate numbers from Locust (Phase 3). ("Picked 60s from the data's update cadence, validated against real hit-rate metrics" > a suspiciously precise made-up number.)

## Good to know (parked)

- **Redis hashes** — store a train's fields as separate sub-fields under one key (update one field without rewriting the whole blob). A plain JSON string via `model_dump_json()` is fine for v1.

## Skipped for now

- **Redis Cluster / sharding** and **Redis pub/sub** — solve scale/messaging problems this project doesn't have. Single-instance, plain key-value is enough. (Pub/sub specifically would only matter for the out-of-scope real-time push feature, so building it now would be unused code.)

---

## What I built

### New file: `app/db/redis_client.py`
Mirrors `app/db/database.py`'s "create one shared connection object at import time" pattern:
```python
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
```
- `redis.asyncio` — the async client (matches the app's async-everywhere style; different from the plain `redis` used by Celery in Day 1's toy).
- `from_url(...)` manages a connection pool internally — created once, reused across all requests, not per-request.
- `decode_responses=True` — return `str` (JSON text) instead of raw `bytes`.

### `app/main.py` lifespan
Added `await redis_client.aclose()` on shutdown, alongside the existing `engine.dispose()` — same lifecycle discipline for the Redis pool as for Postgres.

### `app/api/routes/trains.py`
- Cache **read** at the top: `GET train:{train_no}`, wrapped in `try/except` — any Redis error is swallowed and treated as a miss, so a Redis outage can never break the route (cache is a pure optimization). On a hit, `TrainResponse.model_validate_json(cached)` and return early.
- Cache **write** before the final return (miss path only): `SET` with `result.model_dump_json()` and `ex=60`, also `try/except` — a failed write just means no speed-up next time, never a broken response.
- Side effect (intentional): a cache hit skips the telemetry write, so the route stops writing a Postgres row on *every* call — only once per 60s window per train. Foreshadows Day 3, where Beat takes over continuous telemetry writes.

---

## Bugs found & fixed along the way (via systematic debugging)

The pre-existing `rail_client.py` had *never actually worked* against the real RailRadar API — it was written against a guessed schema. Adding temporary `[DEBUG]` prints at the RailRadar boundary (status, body, and the swallowed exception) surfaced three separate issues in sequence:

1. **Wrong URL + endpoint path.** Code hit `https://api.railradar.in/api/v1/trains/{n}`; real API is `https://api.railradar.in/v1/trains/{n}/live`. Symptom: `404 "Route not found"` (the *path* doesn't exist, not the train).
2. **Wrong auth header.** Code sent `X-API-Key: <key>`; real API wants `Authorization: Bearer <key>`.
3. **Wrong response-shape parsing.** Code looked for `trainNumber`, `trainName`, `sourceStationName`, a `liveData` wrapper, etc. Real shape: `data.train.number`, `data.train.name`, `data.train.source.name` (nested object), `currentLocation` and `delayMinutes` directly under `data`. Symptom: Pydantic `ValidationError` (required string fields came back `None`).
4. **Naive vs. aware datetime mismatch** on the telemetry write. `models.py` stored a timezone-**aware** `datetime.now(timezone.utc)` into a `TIMESTAMP WITHOUT TIME ZONE` (naive) column → `asyncpg.DataError: can't subtract offset-naive and offset-aware datetimes`. Fixed by making the column timezone-aware: `DateTime(timezone=True)`, then dropping + recreating the (throwaway) telemetry table so the new column type took effect.

**Key debugging lesson:** the bare `except Exception: return None` in `rail_client.py` silently swallowed the `ValidationError` and turned every failure into a meaningless 404 — which is exactly why this took so long to diagnose. Had to add temporary prints to see the real error. **Known weak spot to fix properly in Phase 3 Day 1 (structured logging)** — log the real exception instead of hiding it. Debug prints were removed after the investigation.

**Second lesson — testing a short-TTL cache by hand is unreliable.** First manual verification looked broken (responses differed, telemetry count kept climbing) but was actually fine — more than 60s was passing between hand-typed commands, so each key expired and every call was a legitimate miss. A tight, scripted back-to-back test is required: clear the key → curl (miss, +1 row) → curl immediately (hit, +0 rows, identical response) → confirm exactly 1 row added and byte-identical responses. That test passed cleanly.

---

**Status: Day 2 complete.** Cache-aside verified working end to end. Next: Day 3 — Celery Beat periodic scheduling + happy-path telemetry writes (Beat triggers → worker polls RailRadar → row lands in Postgres, off the request path).
