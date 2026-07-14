from celery import Celery
from app.core.config import settings

# How often beat kicks off poll_all_trains, in seconds. 5 min is an
# API-friendly default; tune this for your polling budget.
POLL_INTERVAL_SECONDS = 300.0

celery_app = Celery(
    "live_train_tracker",
    broker = settings.REDIS_URL,
    include = ["app.tasks"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

celery_app.conf.beat_schedule = {
    "poll-all-trains": {
        "task": "app.tasks.poll_all_trains",
        "schedule": POLL_INTERVAL_SECONDS,
    },
}
