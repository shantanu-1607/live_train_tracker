import asyncio
import logging
from datetime import datetime, timezone

import redis
from sqlalchemy import select

from app.celery_app import celery_app
from app.core.config import settings
from app.db.sync_database import SyncSessionLocal
from app.db.models import TrackedTrain, TrainTelemetry
from app.services.rail_client import RailClient

logger = logging.getLogger(__name__)

# one client for the whole worker process; get_live_status spins up its own
# httpx.AsyncClient per call so this is safe to share.
client = RailClient()

# one sync redis client for the whole worker process (redis-py pools internally
# and is thread-safe); used only for the idempotency guard. Reused per call so
# we don't open a fresh connection pool on every task.
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task
def poll_all_trains():
    """Fan-out task run by beat. Just dispatches one child task per active
    train, so it stays fast and does zero HTTP itself."""
    with SyncSessionLocal() as session:
        train_numbers = session.scalars(
            select(TrackedTrain.train_number).where(TrackedTrain.is_active.is_(True))
        ).all()

    for train_no in train_numbers:
        poll_single_train.delay(train_no)

    logger.info("poll_all_trains dispatched %d train(s)", len(train_numbers))
    return {"dispatched": len(train_numbers)}


@celery_app.task(bind=True, max_retries=3)
def poll_single_train(self, train_no: str):
    """Fetch live status for a single train and write one telemetry row.
    Retries with exponential backoff on transient failures, and guards
    against duplicate writes within the same minute."""
    result = asyncio.run(client.get_live_status(train_no))

    if result is None:
        # exponential backoff: 10, 20, 40 ... capped at 10 minutes.
        countdown = min(600, 10 * (2 ** self.request.retries))
        try:
            raise self.retry(countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.warning(
                "giving up on train %s after %d retries", train_no, self.max_retries
            )
            return {"train_number": train_no, "status": "gave_up"}

    # idempotency guard: claim this (train, UTC-minute) BEFORE writing so an
    # overlapping or retried run in the same minute is skipped. Claiming before
    # the write is what keeps two concurrent workers from double-inserting.
    minute_bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = f"polled:{train_no}:{minute_bucket}"

    fresh = redis_client.set(key, "1", nx=True, ex=90)
    if not fresh:
        logger.info("skipped duplicate telemetry for train %s (%s)", train_no, minute_bucket)
        return {"train_number": train_no, "status": "duplicate"}

    try:
        with SyncSessionLocal() as session:
            row = TrainTelemetry(
                train_number=result.number,
                station_code=result.current_station,
                delay_minutes=result.delay,
            )
            session.add(row)
            session.commit()
    except Exception as exc:
        # the write didn't happen, so release the claim -- otherwise this minute
        # bucket would be blocked for 90s and a retry couldn't record the point.
        redis_client.delete(key)
        logger.exception("failed writing telemetry for train %s; retrying", train_no)
        raise self.retry(exc=exc, countdown=min(600, 10 * (2 ** self.request.retries)))

    logger.info(
        "wrote telemetry row for train %s at %s (delay %d)",
        result.number,
        result.current_station,
        result.delay,
    )
    return {"train_number": result.number, "status": "recorded"}
